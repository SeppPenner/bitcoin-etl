# MIT License
#
# Copyright (c) 2018 Evgeny Medvedev, evge.medvedev@gmail.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import math

from bitcoinetl.json_rpc_requests import generate_get_block_by_hash_json_rpc, \
    generate_get_block_hash_by_number_json_rpc, generate_get_transaction_by_id_json_rpc
from bitcoinetl.mappers.block_mapper import BtcBlockMapper
from bitcoinetl.mappers.transaction_mapper import BtcTransactionMapper
from blockchainetl.executors.batch_work_executor import BatchWorkExecutor
from blockchainetl.jobs.base_job import BaseJob
from blockchainetl.utils import rpc_response_batch_to_results, validate_range


# Exports blocks and transactions
class ExportBlocksJob(BaseJob):
    def __init__(
            self,
            start_block,
            end_block,
            batch_size,
            batch_rpc_provider,
            max_workers,
            item_exporter,
            export_blocks=True,
            export_transactions=True):
        validate_range(start_block, end_block)
        self.start_block = start_block
        self.end_block = end_block

        self.rpc_provider = batch_rpc_provider

        self.batch_work_executor = BatchWorkExecutor(batch_size, max_workers)
        self.item_exporter = item_exporter

        self.export_blocks = export_blocks
        self.export_transactions = export_transactions
        if not self.export_blocks and not self.export_transactions:
            raise ValueError('At least one of export_blocks or export_transactions must be True')

        self.block_mapper = BtcBlockMapper()
        self.transaction_mapper = BtcTransactionMapper()

    def _start(self):
        self.item_exporter.open()

    def _export(self):
        self.batch_work_executor.execute(
            range(self.start_block, self.end_block + 1),
            self._export_batch,
            total_items=self.end_block - self.start_block + 1
        )

    def add_input_values(self, block):
        for tx_index, tx in enumerate(block['tx']):
            txids = list(map(lambda vin: vin["txid"] if "txid" in vin else "", tx['vin']))

            transaction_detail_rpc = list(generate_get_transaction_by_id_json_rpc(txids))
            transaction_detail_response = self.rpc_provider.make_request(transaction_detail_rpc)

            for index, response in enumerate(transaction_detail_response):
                n = tx['vin'][index]['vout']
                tx['vin'][index]['value'] = int(int(response['vout'][n]['value']) * math.pow(10, 8))

            block['tx'][tx_index] = tx

        return block

    def _export_batch(self, block_number_batch):

        # get block
        block_hash_rpc = list(generate_get_block_hash_by_number_json_rpc(block_number_batch))
        block_hashes_response = self.rpc_provider.make_request(block_hash_rpc)
        block_hashes = rpc_response_batch_to_results(block_hashes_response)

        # get block details by hash
        block_detail_rpc = list(generate_get_block_by_hash_json_rpc(block_hashes, self.export_transactions))
        block_detail_response = self.rpc_provider.make_request(block_detail_rpc)
        block_detail_results = rpc_response_batch_to_results(block_detail_response)

        # TODO: Factor out to enrich_transactions_job.py
        # # get all the transactions in input
        # if self.export_transactions:
        #     block_detail_results = [self.add_input_values(block_detail_result)
        #                             for block_detail_result in block_detail_results]

        blocks = [self.block_mapper.json_dict_to_block(block_detail_result)
                  for block_detail_result in block_detail_results]

        for block in blocks:
            self._export_block(block)

    def _export_block(self, block):
        if self.export_blocks:
            self.item_exporter.export_item(self.block_mapper.block_to_dict(block))
        if self.export_transactions:
            for tx in block.transactions:
                self.item_exporter.export_item(self.transaction_mapper.transaction_to_dict(tx))

    def _end(self):
        self.batch_work_executor.shutdown()
        self.item_exporter.close()
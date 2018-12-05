# MIT License
#
# Copyright (c) 2018 Omidiora Samuel, samparsky@gmail.com
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

import pytest
from dateutil.parser import parse

from bitcoinetl.providers.rpc import BatchRPCProvider
from bitcoinetl.service.bitcoin_service import BtcService
from blockchainetl.service.graph_operations import OutOfBoundsError
from tests.helpers import skip_if_slow_tests_disabled
from tests.bitcoinetl.job.helpers import get_provider


@pytest.mark.parametrize("date,expected_start_block,expected_end_block", [
    skip_if_slow_tests_disabled(['2009-03-01', 5924, 6028]),
    skip_if_slow_tests_disabled(['2017-01-02', 446189, 446347]),
])
def test_get_block_range_for_date(date, expected_start_block, expected_end_block):
    btc_service = get_new_btc_service()
    parsed_date = parse(date)
    blocks = btc_service.get_block_range_for_date(parsed_date)
    assert blocks == (expected_start_block, expected_end_block)


@pytest.mark.parametrize("date", [
    skip_if_slow_tests_disabled(['2030-01-01'])
])
def test_get_block_range_for_date_fail(date):
    btc_service = get_new_btc_service()
    parsed_date = parse(date)
    with pytest.raises(OutOfBoundsError):
        btc_service.get_block_range_for_date(parsed_date)


@pytest.mark.parametrize("start_timestamp,end_timestamp,expected_start_block,expected_end_block", [
    skip_if_slow_tests_disabled([1235952055, 1235995140, 6029, 6082]),
    skip_if_slow_tests_disabled([1328227200, 1328248800, 165081,165132]),
])
def test_get_block_range_for_timestamps(start_timestamp, end_timestamp, expected_start_block, expected_end_block):
    eth_service = get_new_btc_service()
    blocks = eth_service.get_block_range_for_timestamps(start_timestamp, end_timestamp)
    assert blocks == (expected_start_block, expected_end_block)

def get_new_btc_service():
    rpc_conn = get_provider("online")
    return BtcService(rpc_conn)
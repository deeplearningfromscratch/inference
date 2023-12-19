# Copyright 2019 The MLPerf Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

"""Python demo showing how to use the MLPerf Inference load generator bindings.
"""

from __future__ import print_function

import argparse
import threading
import time
import numpy as np
import array

import mlperf_loadgen

from datetime import datetime

# Global var
NUM_AGENTS = 8
LOOPBACK_LATENCY_S = .001

def f(x, y):
    return (4 + 3*x*y + x**3 + y**2)

def create_responses(n, m, mod = 4):
    r = []
    for i in range(n):
        r.append([f(i,j) for j in range(m + (i%mod))])
    return r
responses = create_responses(1024, 20)

def load_samples_to_ram(query_samples):
    del query_samples
    return


def unload_samples_from_ram(query_samples):
    del query_samples
    return


# Processes queries in NUM_AGENTS slices that complete at different times.
def process_query_async(query_samples, i_slice):
    time.sleep(LOOPBACK_LATENCY_S * (i_slice + 1))
    query_responses = []
    samples_to_complete = query_samples[i_slice:len(query_samples):NUM_AGENTS]
    for j, s in enumerate(samples_to_complete):
        response_array = np.array(responses[s.index], np.int32)
        token = response_array[0]
        time.sleep(.0002)
        response_token = array.array("B", token.tobytes())
        response_token_info = response_token.buffer_info()
        response_token_data = response_token_info[0]
        response_token_size = response_token_info[1] * response_token.itemsize
        mlperf_loadgen.FirstTokenComplete([mlperf_loadgen.QuerySampleResponse(s.id, response_token_data, response_token_size)])
        time.sleep(.02)
        n_tokens = len(response_array)
        response_array = array.array("B", response_array.tobytes())
        response_info = response_array.buffer_info()
        response_data = response_info[0]
        response_size = response_info[1] * response_array.itemsize
        query_responses.append(
            mlperf_loadgen.QuerySampleResponse(
                s.id, response_data, response_size, n_tokens))
    mlperf_loadgen.QuerySamplesComplete(query_responses)


def issue_query(query_samples):
    for i in range(8):
        threading.Thread(target=process_query_async,
                         args=(query_samples, i)).start()


def flush_queries():
    pass


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["performance", "accuracy"], default="performance")
    parser.add_argument("--expected-latency", type=int, default=8000000)
    parser.add_argument("--samples-per-query", type=int, default=8)
    parser.add_argument("--min-query-count", type=int, default=100)
    parser.add_argument("--min-duration-ms", type=int, default=30000)
    return parser.parse_args()


def main():
    args = get_args()
    settings = mlperf_loadgen.TestSettings()
    settings.scenario = mlperf_loadgen.TestScenario.MultiStream
    if args.mode == "performance":
        settings.mode = mlperf_loadgen.TestMode.PerformanceOnly
    else:
        settings.mode = mlperf_loadgen.TestMode.AccuracyOnly
    settings.multi_stream_expected_latency_ns = args.expected_latency
    settings.multi_stream_samples_per_query = args.samples_per_query
    settings.min_query_count = args.min_query_count
    settings.min_duration_ms = args.min_duration_ms
    settings.use_token_latencies = True

    sut = mlperf_loadgen.ConstructSUT(issue_query, flush_queries)
    qsl = mlperf_loadgen.ConstructQSL(
        1024, 128, load_samples_to_ram, unload_samples_from_ram)
    mlperf_loadgen.StartTest(sut, qsl, settings)
    mlperf_loadgen.DestroyQSL(qsl)
    mlperf_loadgen.DestroySUT(sut)


if __name__ == "__main__":
    main()

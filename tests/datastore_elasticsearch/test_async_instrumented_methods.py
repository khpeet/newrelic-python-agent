# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import elasticsearch
import elasticsearch._async.client as async_client
import pytest
from conftest import ES_VERSION
from testing_support.validators.validate_datastore_trace_inputs import validate_datastore_trace_inputs

from newrelic.api.background_task import background_task

RUN_IF_V8 = pytest.mark.skipif(
    ES_VERSION < (8,), reason="Only run for v8+. We don't support all methods in previous versions."
)


@pytest.mark.parametrize(
    "sub_module,method,args,kwargs,expected_index",
    [
        (None, "exists", (), {"index": "contacts", "id": 1}, "contacts"),
        (None, "info", (), {}, None),
        pytest.param(
            None,
            "msearch",
            (),
            {"searches": [{}, {"query": {"match": {"message": "this is a test"}}}], "index": "contacts"},
            "contacts",
            marks=RUN_IF_V8,
        ),
        ("indices", "exists", (), {"index": "contacts"}, "contacts"),
        ("indices", "exists_template", (), {"name": "no-exist"}, None),
        ("cat", "count", (), {"index": "contacts"}, "contacts"),
        ("cat", "health", (), {}, None),
        pytest.param(
            "cluster",
            "allocation_explain",
            (),
            {"index": "contacts", "shard": 0, "primary": True},
            "contacts",
            marks=RUN_IF_V8,
        ),
        ("cluster", "get_settings", (), {}, None),
        ("cluster", "health", (), {"index": "contacts"}, "contacts"),
        ("nodes", "info", (), {}, None),
        ("snapshot", "status", (), {}, None),
        ("tasks", "list", (), {}, None),
        ("ingest", "geo_ip_stats", (), {}, None),
    ],
)
def test_method_on_async_client_datastore_trace_inputs(
    loop, async_client, sub_module, method, args, kwargs, expected_index
):
    expected_operation = f"{sub_module}.{method}" if sub_module else method

    @validate_datastore_trace_inputs(target=expected_index, operation=expected_operation)
    @background_task()
    async def _test():
        if not sub_module:
            await getattr(async_client, method)(*args, **kwargs)
        else:
            await getattr(getattr(async_client, sub_module), method)(*args, **kwargs)

    loop.run_until_complete(_test())


def _test_methods_wrapped(_object, ignored_methods=None):
    if not ignored_methods:
        ignored_methods = {"perform_request", "transport"}

    def is_wrapped(m):
        return hasattr(getattr(_object, m), "__wrapped__")

    methods = {m for m in dir(_object) if not m[0] == "_"}
    uninstrumented = {m for m in (methods - ignored_methods) if not is_wrapped(m)}
    assert not uninstrumented, f"There are uninstrumented methods: {uninstrumented}"


@RUN_IF_V8
def test_async_instrumented_methods_client():
    _test_methods_wrapped(elasticsearch.AsyncElasticsearch)


@RUN_IF_V8
def test_instrumented_methods_client_indices():
    _test_methods_wrapped(async_client.IndicesClient)


@RUN_IF_V8
def test_instrumented_methods_client_cluster():
    _test_methods_wrapped(async_client.ClusterClient)


@RUN_IF_V8
def test_instrumented_methods_client_cat():
    if hasattr(async_client, "CatClient"):
        _test_methods_wrapped(async_client.CatClient)


@RUN_IF_V8
def test_instrumented_methods_client_nodes():
    if hasattr(async_client, "NodesClient"):
        _test_methods_wrapped(async_client.NodesClient)


@RUN_IF_V8
def test_instrumented_methods_client_snapshot():
    if hasattr(async_client, "SnapshotClient"):
        _test_methods_wrapped(async_client.SnapshotClient)


@RUN_IF_V8
def test_instrumented_methods_client_tasks():
    if hasattr(async_client, "TasksClient"):
        _test_methods_wrapped(async_client.TasksClient)


@RUN_IF_V8
def test_instrumented_methods_client_ingest():
    if hasattr(async_client, "IngestClient"):
        _test_methods_wrapped(async_client.IngestClient)

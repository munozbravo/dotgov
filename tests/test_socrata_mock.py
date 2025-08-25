import pytest
import responses
from responses import matchers

from dotgov.socrata import Socrata, DiscoverFilters, ApprovalStatus, Only, Provenance


pytestmark = pytest.mark.unit


CATALOG_PATH = "/api/catalog/v1"


## Sessions


def test_open_close_sets_session_and_headers(domain: str):
    s = Socrata(domain=domain, app_token="token-123")

    assert s.session is None

    s.open()

    try:
        assert s.session is not None
        assert s.session.headers.get("X-App-Token") == "token-123"

    finally:
        s.close()

    assert s.session is None


def test_context_manager_opens_and_closes(domain: str):
    s = Socrata(domain=domain)

    assert s.session is None

    with s as client:
        assert client.session is not None

    assert s.session is None


## Datasets


def test_defaults_include_expected_query_params(
    socrata_default_client: Socrata, mocked: responses.RequestsMock, re_url
):
    params = dict(
        approval_status="approved",
        provenance="official",
        only="dataset",
        explicitly_hidden="false",
        audience="public",
        published="true",
    )

    mocked.add(
        responses.GET,
        re_url(CATALOG_PATH, "offset"),
        status=200,
        json={"resultSetSize": 1, "results": [{"resource": {"id": "id1"}}]},
        match=[matchers.query_param_matcher(params, strict_match=False)],
    )

    rows = list(socrata_default_client.discover())

    assert len(rows) == 1

    u = mocked.calls[0].request.url or ""

    for k in params:
        assert k in u


def test_pagination_uses_limit_and_offset(
    socrata_default_client: Socrata, mocked: responses.RequestsMock, re_url
):
    # First page (offset=0) returns 2 results; second page (offset=2) returns 0
    mocked.add(
        responses.GET,
        re_url(CATALOG_PATH, "offset=0"),
        status=200,
        json={
            "resultSetSize": 2,
            "results": [
                {"resource": {"id": "a"}},
                {"resource": {"id": "b"}},
            ],
        },
    )

    mocked.add(
        responses.GET,
        re_url(CATALOG_PATH, "offset=1000"),
        status=200,
        json={"resultSetSize": 2, "results": []},
    )

    rows = list(socrata_default_client.discover())

    calls = [c.request.url or "" for c in mocked.calls]

    assert [r["resource"]["id"] for r in rows] == ["a", "b"]
    assert any("offset=1000" in c for c in calls)


## Endpoints


def test_format_endpoint_versions_v21(socrata_default_client: Socrata):
    rid = "abcd-1234"

    assert socrata_default_client.version == 2.1
    assert socrata_default_client.format_endpoint(rid) == f"/resource/{rid}.json"


def test_format_endpoint_versions_v30(socrata_v3_client: Socrata):
    rid = "abcd-1234"

    assert socrata_v3_client.version == 3.0
    assert socrata_v3_client.format_endpoint(rid) == f"/api/v3/views/{rid}/query.json"


## query_resource version-specific behavior


def test_query_resource_v21_uses_get_and_limit_in_url_and_paginates(
    socrata_default_client: Socrata, mocked: responses.RequestsMock, re_url
):
    # Arrange
    rid = "abcd-1234"
    path = f"/resource/{rid}.json"

    # First page: offset=0, returns 2 records
    mocked.add(
        responses.GET,
        re_url(path, "$offset=0"),
        status=200,
        json=[{"i": 1}, {"i": 2}],
    )

    # Second page: offset=2, returns 0 records (stop)
    mocked.add(
        responses.GET,
        re_url(path, "$offset=2"),
        status=200,
        json=[],
    )

    # Act
    rows = list(socrata_default_client.query_resource(rid, filters={"limit": 2}))

    # Assert results
    assert [r["i"] for r in rows] == [1, 2]

    # Assert requests
    calls = mocked.calls
    assert len(calls) >= 1
    # All calls are GET to /resource/{rid}.json
    assert all(c.request.method == "GET" for c in calls)
    assert all(path in (c.request.url or "") for c in calls)

    # URL must include $limit, and offsets should progress
    urls = [c.request.url or "" for c in calls]
    assert any("%24limit=" in u for u in urls)
    assert any("%24offset=0" in u for u in urls)
    assert any("%24offset=2" in u for u in urls)


def test_query_resource_v30_uses_post_and_page_payload_and_paginates(
    socrata_v3_client: Socrata, mocked: responses.RequestsMock
):
    # Arrange
    import json as _json

    rid = "abcd-1234"
    path = f"https://{socrata_v3_client.domain}/api/v3/views/{rid}/query.json"

    # Provide 3 sequential POST responses: 2 records, 1 record, then empty to stop
    mocked.add(
        responses.POST,
        path,
        status=200,
        json=[{"i": 1}, {"i": 2}],
    )
    mocked.add(
        responses.POST,
        path,
        status=200,
        json=[{"i": 3}],
    )
    mocked.add(
        responses.POST,
        path,
        status=200,
        json=[],
    )

    # Act
    rows = list(socrata_v3_client.query_resource(rid, filters={"limit": 2}))

    # Assert results
    assert [r["i"] for r in rows] == [1, 2, 3]

    # Assert requests
    calls = mocked.calls
    assert len(calls) >= 2
    assert all(c.request.method == "POST" for c in calls)
    assert all(path == (c.request.url or "") for c in calls)

    # Ensure no $limit/$offset in URL; pagination is via JSON payload 'page'
    urls = [c.request.url or "" for c in calls]
    assert all("%24limit=" not in u and "%24offset=" not in u for u in urls)

    # Check page payload increments pageNumber and includes pageSize
    bodies = [_json.loads((c.request.body or b"{}").decode("utf-8")) for c in calls]

    # Expect at least the first two calls (third may be unnecessary depending on stop logic)
    for idx, body in enumerate(bodies, start=1):
        # page object must exist with positive integers
        assert "page" in body, body
        page = body["page"]
        assert isinstance(page.get("pageNumber"), int) and page["pageNumber"] >= 1
        assert isinstance(page.get("pageSize"), int) and page["pageSize"] >= 1

    # Specifically, first two calls should be pageNumber=1 then 2
    if len(bodies) >= 2:
        assert bodies[0]["page"]["pageNumber"] == 1
        assert bodies[0]["page"]["pageSize"] == 2
        assert bodies[1]["page"]["pageNumber"] == 2
        assert bodies[1]["page"]["pageSize"] == 2


## format_payload tests


def test_format_payload_v21_maps_core_fields_and_extras(domain: str):
    s = Socrata(domain=domain, version=2.1)

    filters = {
        "select": "a,b",
        "where": "x > 1",
        "order": "a DESC",
        "limit": 42,
        # extras that should be carried as $-prefixed keys
        "q": "covid",
        "timeout": 1000,
    }

    payload = s.format_payload(filters=filters.copy())

    # Core SoQL params -> $-prefixed keys in query string
    assert payload["$select"] == "a,b"
    assert payload["$where"] == "x > 1"
    # order is mapped to $order; $group is only present when 'group' is provided
    assert payload["$order"] == "a DESC"
    assert payload.get("$group") is None
    # limit and default offset
    assert payload["$limit"] == 42
    assert payload["$offset"] == 0

    # Extras mapped and prefixed with $
    assert payload["$q"] == "covid"
    assert payload["$timeout"] == 1000

    # v2.1 should not include a page object
    assert "page" not in payload


def test_format_payload_v21_default_limit_is_max(domain: str):
    s = Socrata(domain=domain, version=2.1)

    payload = s.format_payload(filters={})

    assert payload["$limit"] == 1000
    assert payload["$offset"] == 0


def test_format_payload_v30_builds_query_and_page_and_extras(domain: str):
    s = Socrata(domain=domain, version=3.0)

    filters = {
        "select": "a,b",
        "where": "x > 1",
        "group": "g",
        "having": "sum(y) > 0",
        "order": "a DESC",
        "limit": 2,
        # extras included for v3 payload
        "parameters": {"p": "v"},
        "timeout": 1000,
        "includeSystem": True,
        "includeSynthetic": False,
    }

    payload = s.format_payload(filters=filters)

    # Page object present with provided limit
    assert payload["page"]["pageNumber"] == 1
    assert payload["page"]["pageSize"] == 2

    # Query assembled in correct order with spaces as implemented
    expected_query = (
        "SELECT a,b  WHERE x > 1  GROUP BY g  HAVING sum(y) > 0  ORDER BY a DESC"
    )
    assert payload["query"] == expected_query

    # Extras present
    assert payload["parameters"] == {"p": "v"}
    assert payload["timeout"] == 1000
    assert payload["includeSystem"] is True
    assert payload["includeSynthetic"] is False

    # v3 payload should not carry raw 'limit' or $-prefixed params
    assert "limit" not in payload
    assert all(not k.startswith("$") for k in payload.keys())


def test_format_payload_v30_default_limit_is_max(domain: str):
    s = Socrata(domain=domain, version=3.0)

    payload = s.format_payload(filters={})

    assert payload["page"]["pageNumber"] == 1
    assert payload["page"]["pageSize"] == 1000
    # Minimal query when no clauses provided
    assert payload["query"] == "SELECT * "


## Created after creating DiscoverFilters


class DummyResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"resultSetSize": 0, "results": []}


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.last_params = None

    def get(self, url, params=None, **kwargs):
        self.last_params = params
        return DummyResponse()

    def close(self):
        pass


def run_discover_and_capture_params(socrata, filters=None):
    socrata.session = FakeSession()
    list(socrata.discover(filters=filters))
    return socrata.session.last_params


def test_default_filters_serialization():
    s = Socrata(domain="example.org")
    params = run_discover_and_capture_params(s)
    assert params["approval_status"] == "approved"
    assert params["only"] == "dataset"
    assert params["provenance"] == "official"


def test_dict_filters_serialization():
    s = Socrata(domain="example.org")
    params = run_discover_and_capture_params(
        s,
        {
            "approval_status": ApprovalStatus.PENDING,
            "only": Only.MAP,
            "provenance": Provenance.COMMUNITY,
        },
    )
    assert params["approval_status"] == "pending"
    assert params["only"] == "map"
    assert params["provenance"] == "community"


def test_instance_filters_serialization():
    s = Socrata(domain="example.org")
    f = DiscoverFilters(
        approval_status=ApprovalStatus.REJECTED,
        only=Only.FILE,
        provenance=Provenance.OFFICIAL,
    )
    params = run_discover_and_capture_params(s, f)
    assert params["approval_status"] == "rejected"
    assert params["only"] == "file"
    assert params["provenance"] == "official"

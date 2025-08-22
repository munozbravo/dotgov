import re
from collections.abc import Iterator

import pytest
import responses

from dotgov.constants import COLOMBIA
from dotgov.socrata import Socrata


@pytest.fixture
def domain() -> str:
    return COLOMBIA


@pytest.fixture
def api_base(domain: str) -> str:
    return f"https://{domain}"


@pytest.fixture
def mocked() -> Iterator[responses.RequestsMock]:
    """Intercept requests.Session calls"""

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


@pytest.fixture
def socrata_default_client(domain: str) -> Iterator[Socrata]:
    """Context-managed Socrata client for tests (default v2.1)"""

    with Socrata(domain=domain) as client:
        yield client


@pytest.fixture
def socrata_v3_client(domain: str) -> Iterator[Socrata]:
    """Context-managed Socrata client for tests (v3.0)"""

    with Socrata(domain=domain, version=3.0) as client:
        yield client


def api_url(api_base: str, path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path

    return f"{api_base}{path}"


@pytest.fixture
def add_json(api_base: str):
    """Helper to add a json like response"""

    def _add(
        http: responses.RequestsMock,
        method: str,
        path: str,
        payload,
        status: int = 200,
        content_type: str = "application/json",
        headers: dict | None = None,
    ):
        url = api_url(api_base, path)

        http.add(
            method,
            url,
            json=payload,
            status=status,
            headers=headers or {"Content-Type": content_type},
        )

        return url

    return _add


@pytest.fixture
def re_url(api_base: str):
    """Build a compiled regex URL matcher for pagination assertions"""

    def _re(path_prefix: str, contains: str):
        encoded_contains = contains.replace("$", "%24")

        return re.compile(
            rf"^{re.escape(api_base + path_prefix)}\?[^#]*{re.escape(encoded_contains)}.*$"
        )

    return _re

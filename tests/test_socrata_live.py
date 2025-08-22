import itertools
import os
import pytest
from dotenv import load_dotenv

from dotgov.constants import COLOMBIA, COLOMBIA_PROCUREMENT
from dotgov.socrata import Socrata


pytestmark = pytest.mark.integration

LIVE = bool(os.environ.get("DOTGOV_LIVE", ""))

skip_live = pytest.mark.skipif(
    not LIVE, reason="Set DOTGOV_LIVE=1 to enable integration tests."
)

_ = load_dotenv()


@skip_live
def test_list_some_datasets():
    token = os.environ.get("SOCRATA_TOKEN")

    with Socrata(domain=COLOMBIA, retries=2, app_token=token) as s:
        filters = dict(q="covid")
        n = 3

        got = list(itertools.islice(s.discover(filters=filters), n))

        assert len(got) == n


@skip_live
def test_fetch_some_resource():
    token = os.environ.get("SOCRATA_TOKEN")

    with Socrata(domain=COLOMBIA, retries=2, app_token=token) as s:
        n = 5
        filters = dict(limit=n)

        got = list(
            itertools.islice(s.query_resource(COLOMBIA_PROCUREMENT, filters=filters), n)
        )

        assert len(got) == n

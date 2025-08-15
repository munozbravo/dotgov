# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.
``

Project overview

- Purpose: dotgov is a small Python library for accessing government Open Data (Socrata/SODA).
- Python: >= 3.12. Packaging/build uses uv and uv_build.
- Package layout: src/dotgov with a typed package marker (py.typed).

Common commands (use uv)

- Install dev environment (resolves prod + dev groups):
  - uv sync --group dev
- Add/remove dependencies:
  - uv add <package>
  - uv remove <package>
  - Dev-only: uv add --group dev <package>
- Run Python/REPL or a module:
  - uv run python
  - uv run python -m dotgov
- Tests (pytest is a dev dependency; repository may not include tests yet):
  - uv run pytest
  - Run a single test by expression: uv run pytest -k "pattern"
  - Verbose with durations: uv run pytest -vv --durations=10
- Build distribution artifacts:
  - uv build
- Lint/format:
  - No linter/formatter is configured in this repo. If needed, add one via uv (e.g., uv add --group dev ruff black) and document its usage.

Architecture and code structure (big picture)

- Package: src/dotgov
  - Constants (src/dotgov/constants.py)
    - COLOMBIA = "www.datos.gov.co". Convenience domain constant.
  - Socrata client (src/dotgov/socrata.py)
    - Goal: typed, minimal client for the SODA Consumer API.
    - Key enums:
      - Only: DATASET, HREF, MAP
      - PROVENANCE: OFFICIAL, COMMUNITY
      - APPROVAL_STATUS: APPROVED, NOT_READY, PENDING, REJECTED
      - HTTPMethod: GET, POST (used for validating allowed methods)
    - Session lifecycle and retries:
      - Socrata.open() initializes a requests.Session.
        - If app_token provided, sets X-App-Token header; otherwise warns about rate limits.
      - Optional urllib3 Retry is mounted via HTTPAdapter when retries is set (500/502/503/504 with backoff).
      - Context manager support: **enter**/**exit** handle open/close and propagate exceptions.
    - Request execution (\_make_request):
      - Builds https://{domain}{endpoint}; validates method; executes via session.
      - Accepts JSON (application/json, application/vnd.geo+json) and text/plain (parsed as JSON); unknown content types raise.
      - Logs HTTP errors and returns None on failures.
    - Dataset discovery (get_datasets):
      - Calls /api/catalog/v1 with defaults: published, public, approval_status=approved, provenance=official, only=dataset, explicitly_hidden=False.
      - Supports optional order and a whitelist of filters (ids, q, min_should_match, approval_status, provenance, only, explicitly_hidden) with validation against enums.
      - Streams/paginates results using MAX_LIMIT=1000 and offset, yielding each dataset dict.
    - Resource access (get_resource):
      - Builds endpoint via format_endpoint(resource_id, version) for SODA 2.1 (/resource/{id}.json), 3.0 (/api/v3/views/{id}/query.json), or legacy.
      - Supports SoQL parameters via kwargs ($select, $where, $order, $group, $limit) plus pagination ($limit/$offset) and yields records.
    - Metadata (get_metadata):
      - Accepts str or list of ids and leverages get_datasets(ids=[...]) to collect metadata for those ids.
  - Typing: src/dotgov/py.typed declares the package as typed (PEP 561). No mypy config is present in the repo.

Quick usage examples

- List datasets from a Socrata domain (approved, official, public by default):

  - uv run python - <<'PY'
    from dotgov.socrata import Socrata
    from dotgov.constants import COLOMBIA

    with Socrata(domain=COLOMBIA, retries=3) as s:
      for dataset in s.get_datasets(order="name ASC"):
      print(dataset)
      if i >= 4: break

  - PY

- Fetch records from a dataset with SoQL:

  - uv run python - <<'PY'
    from dotgov.socrata import Socrata
    from dotgov.constants import COLOMBIA

    DATASET_ID = "abcd-1234" # replace with a real resource id
    with Socrata(domain=COLOMBIA, retries=3) as s:
      rows = s.get_resource(DATASET_ID, select="\*", where=None, order=None, limit=100)
      for i, row in enumerate(rows):
      print(row)
      if i >= 4: break

  - PY

Repository notes

- pyproject.toml defines:
  - project metadata and dependencies
  - build-system using uv_build
  - dependency-groups.dev: bpython, marimo, pytest
- README.md is minimal; see this file for development guidance.

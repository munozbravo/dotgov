from enum import Enum
import logging

from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from urllib3.util.retry import Retry
import requests


logger = logging.getLogger(__name__)


class Only(Enum):
    CHART = "chart"
    DATASET = "dataset"
    FILTER = "filter"
    LINK = "link"
    MAP = "map"
    MEASURE = "measure"
    STORY = "story"
    VISUALIZATION = "visualization"


class Provenance(Enum):
    OFFICIAL = "official"
    COMMUNITY = "community"


class ApprovalStatus(Enum):
    APPROVED = "approved"
    NOT_READY = "not_ready"
    PENDING = "pending"
    REJECTED = "rejected"


class HTTPMethod(Enum):
    GET = "get"
    POST = "post"


class Socrata:
    """Class to interact with SODA API"""

    MAX_LIMIT = 1000

    PREFIX = "https://"

    def __init__(
        self,
        domain: str,
        version: float = 2.1,
        app_token: str | None = None,
        retries: int | None = None,
    ) -> None:
        """Socrata Instantiation.

        Parameters
        ----------
        domain : str
            Target domain (without scheme)
        version : float
            SODA API version, default 2.1
        app_token : str | None
            Socrata application token
        retries : int | None
            Number of attempts to retry request
        """
        if not domain:
            raise Exception("A domain is required.")

        self.domain = domain
        self.version = version
        self.app_token = app_token
        self.retries = retries
        self.session: requests.Session | None = None

    def open(self):
        """Initialize the requests session if not already open."""
        if self.session is not None:
            return

        self.session = requests.Session()

        if self.app_token:
            self.session.headers.update({"X-App-Token": self.app_token})

        else:
            logger.info("You may be rate-limited. Register app token.")

        if self.retries is not None and self.retries > 0:
            retry_strategy = Retry(
                total=self.retries,
                allowed_methods=[h.name for h in HTTPMethod],
                status_forcelist=(500, 502, 503, 504),
                backoff_factor=0.5,
            )

            adapter = HTTPAdapter(max_retries=retry_strategy)

            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

    def close(self):
        """Close the requests session if open."""
        if self.session is not None:
            self.session.close()
            self.session = None

    def __enter__(self):
        """Open session and return self for use in context manager."""
        self.open()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close session and optionally log exceptions.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception class raised in the `with` block or None if no exception.
        exc_value : BaseException | None
            Exception raised in the `with` block or None if no exception.
        traceback : types.TracebackType | None
            A traceback object containing the stack trace, or None if no exception.
        """
        self.close()

        if exc_type:
            logger.error(f"Error during HTTP request: {exc_value}")

        # Returning False so exceptions propagate
        return False

    def discover(
        self,
        filters: dict | None = None,
        **kwargs,
    ):
        """Returns datasets associated with the domain.

        Parameters
        ----------
        filters : dict | None
            Additional query parameters for the request
            (attribution, categories, domains, ids, only, provenance, query, tags, limit)
        """
        if not self.session:
            self.open()

        endpoint = "/api/catalog/v1"
        uri = "{}{}{}".format(self.PREFIX, self.domain, endpoint)

        n = 0
        offset = 0

        defaults = {
            "published": "true",
            "audience": "public",
            "explicitly_hidden": "false",
            "search_context": self.domain,
            "approval_status": ApprovalStatus.APPROVED.value,
            "provenance": Provenance.OFFICIAL.value,
            "only": Only.DATASET.value,
            "limit": self.MAX_LIMIT,
            "offset": offset,
        }

        # Validate any provided filters
        if filters:
            possible = [
                "approval_status",
                "attribution",
                "categories",
                "domains",
                "ids",
                "names",
                "only",
                "provenance",
                "query",
                "q",
                "tags",
                "limit",
            ]

            for key, value in filters.items():
                if key not in possible:
                    raise TypeError(f"Unexpected keyword argument {key}")

                if key == "approval_status" and value not in [
                    s.value for s in ApprovalStatus
                ]:
                    values = [s.value for s in ApprovalStatus]
                    raise ValueError(f"Value of {key} not in {values}")

                if key == "provenance" and value not in [p.value for p in Provenance]:
                    values = [p.value for p in Provenance]
                    raise ValueError(f"Value of {key} not in {values}")

                if key == "only" and value not in [o.value for o in Only]:
                    values = [o.value for o in Only]
                    raise ValueError(f"Value of {key} not in {values}")

                for ks in ["attribution", "query", "q"]:
                    if key == ks and not isinstance(value, str):
                        raise ValueError(f"Value of {key} should be a string.")

                for kl in ["categories", "domains", "ids", "names", "tags"]:
                    if key == kl and not isinstance(value, list):
                        raise ValueError(f"Value of {key} should be a list of strings.")

                if key == "limit" and not isinstance(value, int):
                    raise ValueError(f"Value of {key} should be an integer.")

            params = {k: filters.pop(k, None) for k in possible}

            params = {k: v for k, v in params.items() if v is not None}

            params = {**defaults, **params}

        else:
            params = defaults.copy()

        while True and self.session is not None:
            try:
                response = self.session.get(uri, params=params, **kwargs)
                response.raise_for_status()

                result_set = response.json()

                if result_set is not None:
                    set_size = result_set.get("resultSetSize", 0)

                    if n >= set_size:
                        logger.info(f"{n} datasets, reached result set size.")
                        break

                    datasets = result_set.get("results", [])

                    if datasets:
                        n += len(datasets)

                        offset += params.get("limit", len(datasets))
                        params.update({"offset": offset})

                        logger.info(f"{n} datasets, offsetting to {offset}")

                        yield from datasets

                    else:
                        logger.info("No datasets to yield.")
                        break
                else:
                    logger.error("No result received for datasets request.")
                    break

            except HTTPError as e:
                logger.error(f"HTTP Error: {e}")
                break

            except Exception as e:
                logger.error(e)
                break

    def format_endpoint(self, identifier: str):
        """Format the correct endpoint for each SODA API version.

        Parameters
        ----------
        identifier : str
            Resource ID
        """
        if self.version > 2.1:
            fmtstr = f"/api/v3/views/{identifier}/query.json"
        elif self.version == 2.1:
            fmtstr = f"/resource/{identifier}.json"
        else:
            fmtstr = f"/api/views/{identifier}.json"

        return fmtstr

    def format_payload(self, filters: dict):
        """Format required payload for request.

        Parameters
        ----------
        filters : dict
            Query parameters for the request
            (select, where, group, having, order, limit, etc)
        """

        if "where" not in filters or not filters.get("where", ""):
            logger.info("WHERE clause recommended to filter data returned.")

        if "order" not in filters or not filters.get("order", ""):
            logger.info("ORDER clause recommended for deterministic pagination.")

        if self.version > 2.1:
            page = 1

            query = "SELECT * "

            minimal = {
                "query": query,
                "page": {"pageNumber": page, "pageSize": self.MAX_LIMIT},
            }

            limit = filters.pop("limit", None)

            if limit:
                minimal["page"]["pageSize"] = limit

            select = filters.pop("select", None)

            if select:
                query = f"SELECT {select} "

            where = filters.pop("where", None)

            if where:
                query = f"{query} WHERE {where} "

            group = filters.pop("group", None)

            if group:
                query = f"{query} GROUP BY {group} "

            having = filters.pop("having", None)

            if group and having:
                query = f"{query} HAVING {having} "

            order = filters.pop("order", None)

            if order:
                query = f"{query} ORDER BY {order}"

            minimal.update({"query": query})

            extra = {
                k: v
                for k, v in filters.items()
                if k
                in [
                    "parameters",
                    "timeout",
                    "includeSystem",
                    "includeSynthetic",
                ]
                and v is not None
            }

            payload = {**minimal, **extra}

        else:
            offset = 0

            minimal = {"$offset": offset}

            params = {
                "$select": filters.pop("select", None),
                "$where": filters.pop("where", None),
                "$group": filters.pop("group", None),
                "$having": filters.pop("having", None),
                "$order": filters.pop("order", None),
                "$limit": filters.pop("limit", self.MAX_LIMIT),
            }

            params = {k: v for k, v in params.items() if v is not None}

            params = {**minimal, **params}

            extra = {
                f"${k}": v
                for k, v in filters.items()
                if k in ["q", "timeout"] and v is not None
            }

            payload = {**params, **extra}

        return payload

    def query_resource(
        self,
        identifier: str,
        filters: dict | None = None,
        **kwargs,
    ):
        """Returns the data for a specific dataset.

        Parameters
        ----------
        identifier : str
            Resource ID
        filters : dict | None
            Additional clause parameters for the request
            (select, where, group, having, order, limit, etc)
        """
        endpoint = self.format_endpoint(identifier=identifier)
        uri = "{}{}{}".format(self.PREFIX, self.domain, endpoint)

        n = 0
        page = 1
        offset = 0

        if filters:
            payload = self.format_payload(filters=filters)

        else:
            logger.info("Filters recommended to limit amount of data returned.")

            minimal = {"limit": self.MAX_LIMIT}
            payload = self.format_payload(filters=minimal)

        while True and self.session is not None:
            try:
                if self.version > 2.1:
                    response = self.session.post(uri, json=payload, **kwargs)
                else:
                    response = self.session.get(uri, params=payload, **kwargs)

                response.raise_for_status()

                records = response.json()

                if records:
                    n += len(records)

                    page += 1

                    if self.version > 2.1:
                        payload["page"]["pageNumber"] = page

                    else:
                        offset += payload.get("$limit", len(records))
                        payload.update({"$offset": offset})

                    logger.info(f"{n} records so far, on to page {page}")

                    yield from records

                else:
                    logger.info("No records to yield.")
                    break

            except HTTPError as e:
                logger.error(f"HTTP Error: {e}")
                break

            except Exception as e:
                logger.error(e)
                break


def create_where_clause(**kwargs):
    """Helper function to create WHERE clause.

    Assumes AND concatenation of kwargs, treatment differing based on value type.
    Tuple (2) values are used as lower an upper bounds.
    Int or Float values are used as greater than threshold.
    Lists and Sets are used to match against a set of possible values `in(...)`.
    Strings are used for fuzzy matching.
    Tuples (3, 4) values for
    """
    clause = ""

    for k, value in kwargs.items():
        if isinstance(value, tuple) and len(value) == 2:
            lower, upper = value

            if type(lower) is not type(upper):
                raise ValueError(f"Type of values in {k} should be the same")

            if lower < upper:
                q = f"{k} between '{lower}' and '{upper}'"

                clause = f"{clause} AND {q}" if clause else q

        if isinstance(value, (int, float)):
            q = f"{k} > {value}"

            clause = f"{clause} AND {q}" if clause else q

        if isinstance(value, (list, set)):
            q = f"{k} in{tuple(v for v in value)}"

            clause = f"{clause} AND {q}" if clause else q

        if isinstance(value, str):
            splat = "%".join(value.split())
            q = f"upper({k}) like upper('%{splat}%')"

            clause = f"{clause} AND {q}" if clause else q

        # TODO: include location data functions
        # ["within_circle", "within_box", "within_polygon"]
        # $where=within_circle(location, 47.65, -122.33, 500)
        # $where=within_box(location, 47.70, -122.35, 47.60, -122.30)
        # $where=within_polygon(location, 'MULTIPOLYGON(((-122.35 47.70, -122.34 47.60, -122.30 47.65, -122.35 47.70)))')

    return clause

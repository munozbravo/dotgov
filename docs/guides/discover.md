# Discover datasets

Use `Socrata.discover` to page through datasets:

```python
from dotgov.socrata import Socrata, Only
from dotgov.constants import SEATTLE


with Socrata(domain=SEATTLE, version=3.0) as s:
    filters = {"only": Only.DATASET.value, "limit": 100}

    for ds in s.discover(filters=filters):
        print(ds["resource"]["name"])
```

<!-- prettier-ignore -->
!!! info "Note"
    `dotgov` includes enums for [`Only`](../api/socrata.md#dotgov.socrata.Only), [`Provenance`](../api/socrata.md#dotgov.socrata.Provenance) and [`ApprovalStatus`](../api/socrata.md#dotgov.socrata.ApprovalStatus), fields that can be used as filters in the Discover API.

    The library also provides a [`DiscoverFilters`](../api/socrata.md#dotgov.socrata.DiscoverFilters) Pydantic model that defines all filters that a user would be able to specify.

    You can find more information about filters allowed on the [Discovery API](https://dev.socrata.com/docs/other/discovery#?route=overview){target="\_blank"} page.

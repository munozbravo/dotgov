# Query a resource

## **SODA API** based portal

`Socrata.query_resource(identifier, filters)` yields records.

<!-- prettier-ignore -->
!!! info "Check out the API Reference"
    Check out [`Payload`](../api/socrata.md#dotgov.socrata.Payload) in the [API Reference](../api/socrata.md) for details on allowed filters.

    The class helps build correct filters for each version.

<!-- prettier-ignore -->
!!! tip "Provide `where` and `order` clauses"
    WHERE clause is recommended to filter data returned. For 3.0 this is part of the `query`.

    ORDER clause is recommended for deterministic pagination.

### Build WHERE clauses

<!-- prettier-ignore -->
!!! info "Check out the API Reference"
    Check out [`create_where_clause`](../api/socrata.md#dotgov.socrata.create_where_clause) in the [API Reference](../api/socrata.md) for details.

    The function builds a WHERE clause from keyword arguments, assuming `AND` between provided arguments.

    Keys are dataset dependent. They represent fields (columns) in the dataset.

    Value types of provided arguments determine how they are used.

```python
from dotgov.socrata import create_where_clause

where = create_where_clause(priority=(1, 3), status=["OPEN", "CLOSED"], description="assault")

# e.g. "priority between 1 and 3 AND status in('OPEN', 'CLOSED') AND upper(description) like upper('%assault%')"
```

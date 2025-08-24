# Build WHERE clauses

<!-- prettier-ignore -->
!!! tip "Tip"
    Check out [`create_where_clause`](../api/socrata.md#dotgov.socrata.create_where_clause) in the [API Reference](../api/socrata.md) for details. The function builds a WHERE clause for a query, assuming `AND` between provided arguments

Value types of provided arguments determine how they are used:

- tuple[str, str | int, int | float, float]
  Values used as lower and upper bounds.
- int | float
  Values used as `greater than` threshold.
- list | set
  Values used to match against a set of possible values `in(...)`.
- str
  Values used for string fuzzy matching.

```python
from dotgov.socrata import create_where_clause

where = create_where_clause(priority=(1, 3), status=["OPEN", "CLOSED"], description="assault")

# e.g. "priority between 1 and 3 AND status in('OPEN', 'CLOSED') AND upper(description) like upper('%assault%')"
```

# Query a resource

`Socrata.query_resource(identifier, filters)` yields records.

- Filters (2.1): `$select`, `$where`, `$group`, `$having`, `$order`, `$limit`
- Filters (3.0): `query`, `page`, `parameters`, `timeout`, `includeSystem`, `includeSynthetic`

<!-- prettier-ignore -->
!!! tip "Provide `where` and `order` clauses"
    WHERE clause is recommended to filter data returned. For 3.0 this is part of the `query`.

    ORDER clause is recommended for deterministic pagination.

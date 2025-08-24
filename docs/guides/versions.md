# API versions

There are two main version of the SODA API.

Version 2.1 was launched in 2015 and introduced different advanced functions for filtering and analysis, as well as geospatial datatypes and output formats. It uses `GET` requests, and filtering and pagination of results is done through query parameters (query strings as part of the url).

Version 3.0 is being deployed during 2025 and, besides changing the dataset endpoints, specifies that query requests **must** be sent with a valid [application token](https://dev.socrata.com/docs/app-tokens){target="\_blank"}, preferably sent using the `POST` request method (this means no url query parameters).

<!-- prettier-ignore -->
!!! info "More info on versions"
    You can find more information on versions in SODA's [API Docs](https://dev.socrata.com/docs/endpoints){target="_blank"} endpoint page.

    You can tell what version a dataset is using by looking at the endpoint.

    Version 3.0 uses `/api/v3/views/IDENTIFIER/query.json`

    Version 2.1 uses `/resource/IDENTIFIER.json`

`dotgov`'s `Socrata` class provides `format_endpoint` and `format_payload` methods to take care of the details on where to submit requests to and how to provide filtering and pagination details. The `query_resource` method internally uses these methods to determine how to submit the request.

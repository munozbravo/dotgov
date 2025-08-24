# dotgov

## What is it?

A lightweight Python library for accessing government Open Datasets.

## Install

Inside your Python project run:

```bash
uv add dotgov
```

<!-- prettier-ignore -->
!!! info "What is `uv`?"
    `uv` is the recommended Python package and project manager.

    You can find installation details for your platform in `uv`'s [Installation](https://docs.astral.sh/uv/getting-started/installation/){target="\_blank"} page.

    `uv add` assumes you are working in a [Python project](https://docs.astral.sh/uv/guides/projects/){target="\_blank"} with a virtual environment.

## Quickstart

### **SODA API** based portal

<!-- prettier-ignore -->
!!! tip "Finding Open Datasets based on [SODA API](https://dev.socrata.com/consumers/getting-started){target="\_blank"}"
    You can search the [Open Data Network](https://www.opendatanetwork.com/){target="\_blank"} for datasets from locations or subjects of interest around the world.

A minimal example fetching records:

```python
import os

from dotenv import load_dotenv
from dotgov.socrata import Socrata


_ = load_dotenv()

app_token = os.getenv("SOCRATA_TOKEN")


with Socrata(domain="data.seattle.gov", version=3.0, app_token=app_token) as s:
    filters = {
        "where": "datetime between '2025-08-01T00:00:00' and '2025-08-21T23:59:59'",
    }

    for record in s.query_resource("kzjm-xkqj", filters=filters):
        print(record)
```

<!-- prettier-ignore -->
!!! info "What is `kzjm-xkqj`?"
    In the SODA API each dataset is identified by a unique 4x4 identifier.

    For example, `kzjm-xkqj` is the dataset ID for **Seattle Real Time Fire 911 Calls**.

    You can find details of each dataset in its [About](https://data.seattle.gov/Public-Safety/Seattle-Real-Time-Fire-911-Calls/kzjm-xkqj/about_data){target="\_blank"} page.

# Getting started

## Install

The package requires Python 3.11 or newer.

```bash
pip install biomero-schema
```

For development, clone the repository and install it in editable mode:

```bash
pip install -e .
```

The repository also provides [Pixi](https://pixi.sh/) tasks:

```bash
pixi run test
pixi run json-schema
```

## Validate a workflow descriptor

```bash
biomero-schema validate workflow.json
```

Parse it and show a summary:

```bash
biomero-schema parse workflow.json
```

Use `--pretty` for the complete parsed representation or `--json` for JSON.

## Use a cross-service contract

Consumers should import the Pydantic model rather than copying its fields:

```python
from biomero_schema.zarr import CanonicalZarrSource

source = CanonicalZarrSource.from_dict(payload)
wire_payload = source.to_dict()  # stable camelCase representation
json_schema = CanonicalZarrSource.model_json_schema()
```

Models reject unknown fields and are immutable after construction. This makes
contract drift visible at the boundary where it occurs.

# BIOMERO Schema

Shared, versioned Pydantic contracts for the BIOMERO ecosystem.

[Documentation](https://nl-bioimaging.github.io/biomero-schema/) ·
[Python API](https://nl-bioimaging.github.io/biomero-schema/api/workflow/) ·
[Pixel identity reference](https://nl-bioimaging.github.io/biomero-schema/pixel-identity/)

The package keeps two contract areas separate:

- `biomero_schema.models` is BIOMERO's normalized representation of a workflow
  descriptor.
- `biomero_schema.zarr` and `biomero_schema.imports` define internal
  cross-service contracts for managed Zarr sources, pixel identity, shallow
  collections, and importer lifecycle operations.

## Workflow descriptors

Workflow providers normally describe their tools using an external workflow
format. The `biomero` runtime detects and converts supported formats into the
validated `WorkflowSchema` from this package:

```text
BIAFLOWS descriptor.json ─┐
                         ├─> biomero adapters ─> WorkflowSchema ─> BIOMERO services
BILAYERS config.yaml ─────┘
```

Currently supported inputs are:

| Provider format | BIOMERO support |
| --- | --- |
| [BILAYERS `config.yaml`](https://bilayers.org/understanding-config/) | Converts the container, command, citations, inputs, parameters, and declared outputs. This is the preferred route for Zarr-to-Zarr and Plate-aware workflows. |
| [BIAFLOWS/Cytomine descriptor](https://neubias-wg5.github.io/creating_bia_workflow_and_adding_to_biaflows_instance.html) | Converts the supported legacy `cytomine-0.1` subset. It remains useful for established TIFF-oriented BIAFLOWS workflows. |
| Native `biomero-0.1` descriptor | Validates directly. This is primarily BIOMERO's normalized service representation, although integrations may produce it explicitly. |

CWL and OpenAPI descriptors are not yet supported. The adapters are maintained
in [`biomero.schema_parsers`](https://github.com/NL-BioImaging/biomero/blob/main/biomero/schema_parsers.py),
not in this schema package. This repository therefore documents what the
normalized model can represent; the adapter determines which fields from an
external format are currently converted.

See [Workflow descriptors](https://nl-bioimaging.github.io/biomero-schema/workflow-descriptors/)
for the conversion boundary and supported mappings.

## Installation

Python 3.11 or newer is required.

```bash
pip install biomero-schema
```

For development:

```bash
git clone https://github.com/NL-BioImaging/biomero-schema.git
cd biomero-schema
pip install -e .
```

The repository also supports [Pixi](https://pixi.sh/):

```bash
pixi run test
```

## Native descriptor validation

The CLI validates the normalized BIOMERO descriptor. Conversion of BILAYERS or
BIAFLOWS descriptors is performed by the `biomero` runtime before validation.

```bash
biomero-schema validate descriptor.json
biomero-schema parse descriptor.json
biomero-schema parse descriptor.json --pretty
biomero-schema schema
```

A maintained native example is available at
[`tests/example_workflow.json`](tests/example_workflow.json).

## Cross-service contracts

Consumers should import the shared models rather than duplicating JSON fields:

```python
from biomero_schema.zarr import CanonicalZarrSource

source = CanonicalZarrSource.from_dict(payload)
wire_payload = source.to_dict()
json_schema = CanonicalZarrSource.model_json_schema()
```

The camelCase output from `to_dict()` is the stable wire representation. Every
contract family carries its own integer `schema`, independently of the workflow
descriptor version.

The shallow-Zarr contracts are experimental BIOMERO storage contracts inspired
by OME-NGFF RFC 8. They are not a replacement for OME-NGFF Collections and are
not requirements for third-party workflows.

## Documentation development

```bash
python -m pip install -e .
python -m pip install -r docs/requirements.txt
mkdocs serve
```

Use `mkdocs build --strict` to reproduce the documentation CI build. See
[`docs/contributing.md`](docs/contributing.md) for publishing details.

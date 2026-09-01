# BIOMERO Schema

`biomero-schema` is the shared, versioned contract package for BIOMERO
services. It supplies Pydantic models, stable JSON representations, generated
JSON Schema, and a command-line validator.

The package has two deliberately separate responsibilities:

- **Workflow descriptors** describe portable workflows, their containers,
  inputs, outputs, parameters, resources, and command line.
- **Cross-service contracts** describe BIOMERO-owned hand-offs, including
  canonical Zarr sources, pixel identities, shallow Zarr collections, and
  importer lifecycle operations.

This separation matters. A FAIR workflow provider should only need the
workflow descriptor. BIOMERO's storage optimization records are internal
contracts between services and are not additions to BILAYERS or OME-NGFF.

## Choose a starting point

| I want to… | Read… |
| --- | --- |
| install the package or validate a descriptor | [Getting started](getting-started.md) |
| describe a workflow | [Workflow descriptors](workflow-descriptors.md) |
| understand `.biomero-shallow.json` | [Zarr contracts](zarr-contracts.md) |
| interpret `dataCode`, `instanceCode`, or another identity field | [Pixel identity](pixel-identity.md) |
| request importer-owned shallow normalization | [Import lifecycle](import-lifecycle.md) |
| integrate another BIOMERO service | [Versioning and compatibility](versioning.md) and the [Python API](api/zarr.md) |

!!! warning "Experimental shallow-Zarr contracts"
    The shallow-Zarr and pixel-identity models capture BIOMERO's current
    implementation while OME-NGFF collections and RFC-8 evolve. They are
    versioned and backward-compatible, but should not be presented as an
    adopted OME-NGFF interchange format.

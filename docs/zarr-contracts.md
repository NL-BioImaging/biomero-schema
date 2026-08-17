# Zarr interchange contracts

The models in `biomero_schema.zarr` describe records exchanged between
BIOMERO-owned services when locating canonical Zarr data, recording the exact
input to a run, and comparing pixel identities. They are deliberately separate
from the workflow descriptor models in `biomero_schema.models`.

The package owns the wire format and validation for these records. Consumers
should import the Pydantic models instead of maintaining local copies. The
camelCase form returned by `to_dict()` is the stable JSON representation;
`model_json_schema()` generates JSON Schema for consumers that cannot import
Python packages.

The contracts do not prescribe how a service stores Zarr data, locks files,
accesses OMERO, records events, or reconstructs an RFC-8-style shallow copy.
Those operations remain the responsibility of the consuming service. Likewise,
OME-NGFF and RFC-8 metadata remain external standards and are not redefined by
this package.

## Models

- `PixelIdentity` identifies the pixels at one image or label node using an
  ISCC-BIO/IMAGEWALK result plus guards such as shape, axes, dtype, and coordinate
  transformations.
- `CanonicalZarrSource` locates one managed canonical Zarr generation and binds
  it to its OMERO source object and pixel identity. It can also encode/decode the
  string values used in an OMERO MapAnnotation with namespace
  `biomero.zarr.source`.
- `CanonicalInput` records which canonical source generation was used for one
  selected workflow input.
- `CanonicalInputManifest` wraps the ordered inputs with their workflow and
  export-task IDs for the event snapshot and task-side recovery file.

Each model has its own integer `schema` field. This version is independent of
`BIOMERO_SCHEMA_VERSION`, which versions workflow descriptors. Contract changes
must remain backward compatible within a schema version; breaking wire changes
require a new schema version and an explicit migration in consumers.

## Example

```python
from biomero_schema.zarr import CanonicalZarrSource

source = CanonicalZarrSource.from_dict(payload)
wire_payload = source.to_dict()
map_annotation_values = source.to_annotation_values()
json_schema = CanonicalZarrSource.model_json_schema()
```

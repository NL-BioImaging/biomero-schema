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
- `CanonicalPlateSource` carries that contract for every image and label node
  in a Plate. OMERO persistence uses a compact `CanonicalPlateIndex` plus
  bounded `CanonicalPlateImageRecord` and `CanonicalPlateLabelRecord`
  annotations, avoiding PostgreSQL's indexed map-value size limit. The
  in-memory and event representation remains one `CanonicalPlateSource`, and
  readers can still accept the earlier monolithic Plate annotation.
- `CanonicalInput` records which canonical source generation was used for one
  selected workflow input. Its optional `transferArtifact` binds the source to
  the exact Zarr store name placed in the workflow input directory. Older
  events without this field remain valid; consumers must then use identity
  matching and reject ambiguous duplicate identities. The selected OMERO ID may
  differ from the canonical source ID when a derived shallow Image or Plate is
  reconstructed from its original source.
- `CanonicalInputManifest` wraps the ordered inputs with their workflow and
  export-task IDs for the event snapshot.
- `ShallowImageReference` binds an omitted returned image node to its managed
  canonical source, verified returned-pixel identity, and retained label nodes.
- `ShallowCollection` is the small RFC-8-shaped BIOMERO storage record written
  as `.biomero-shallow.json`. It supports multiple image-node references so the
  same contract can later represent plate results. This is an internal
  cross-service record, not an OME-NGFF or BILAYERS extension that workflow
  providers must understand.
- `ShallowZarrReference` locates one image node and its retained labels in a
  managed shallow collection. BIOMERO attaches its string encoding to the
  corresponding primary OMERO result object with namespace
  `biomero.zarr.shallow`. The same reference may be attached to compatibility
  label projections. Consumers must validate it against
  `.biomero-shallow.json`; the annotation is an index, not authority.
- `ShallowPlateReference` is the compact Plate-level equivalent. It points to
  the collection and canonical source generation without copying every
  per-image identity into an OMERO MapAnnotation.
- `ZarrImportOptions` carries optional per-order registration behavior between
  Import Results and BIOMERO.importer. Its default uses canonical source pixels;
  `platePixelSource=label` requires one concrete label name and creates a
  label-backed Plate view without copying the label arrays.

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

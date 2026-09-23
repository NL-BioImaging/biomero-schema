# Zarr interchange contracts

This page maps the contract family and its responsibilities. For the meaning
of every ISCC and semantic guard field, see the dedicated
[Pixel identity reference](pixel-identity.md). For operation ordering and
legacy upcasting, see [Import lifecycle](import-lifecycle.md).

## Import lifecycle envelope

Importer orchestration is intentionally separate from workflow descriptors
and from stored Zarr manifests. `ImportOptionsEnvelope` schema 2 carries the
registration controls and an ordered list of optional native lifecycle
operations in the existing importer order `import_options` field.

The first operation, `biomero.shallow-zarr`, requests shallow-result preparation
after any converter/container preprocessing and before OMERO registration.
Without remote receipts, the importer performs comparison and fail-safe shallow
normalization locally. With trusted receipts, it validates normalization already
performed by the remote helper before reusing the shallow collection. The
operation carries the exact `CanonicalInputManifest`; uncertain or changed
full data is retained. Identity parallelism is deployment configuration and is
not client input. See [Remote shallower contracts](remote-shallower-contracts.md)
for the remote hand-off.

Legacy flat schema-1 `ZarrImportOptions` payloads and empty options upcast to a
schema-2 envelope with no operations. They therefore preserve the established
import path.

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
accesses OMERO, records events, or reconstructs a shallow result.
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
- `TRANSFER_INPUT_MARKER` reserves `.biomero-input.json` for one serialized
  `CanonicalInput` written into a temporary workflow-transfer Zarr. The event
  snapshot remains authoritative; importers use the marker only to bind a
  renamed result to one expected input before verifying its pixel identity.
- `ShallowCollection` is the scientific graph: image nodes, label nodes and
  their source relationships. It deliberately contains no OMERO IDs, managed
  roots, pixel identities, workflow IDs or receipts.
- `ShallowBindings` associates every graph node with BIOMERO's canonical-source
  and pixel-identity records. Local and inherited labels use the same
  `ZarrLabelComponent` contract.
- `ShallowManifest` is the versioned private record written as
  `.biomero-shallow.json`. It combines the graph and bindings with workflow and
  transfer provenance under `format: biomero-shallow-zarr` and `schema: 2`.
  It is not RFC-8 metadata. A manifest must contain at least one image but may
  contain no labels.
- `ShallowZarrReference` locates one image node and its retained labels in a
  managed shallow collection. BIOMERO attaches its string encoding to the
  corresponding primary OMERO result object with namespace
  `biomero.zarr.shallow`. The same reference may be attached to compatibility
  label projections. Consumers must validate it against
  `.biomero-shallow.json`; the annotation is an index, not authority.
  Its label list may also be empty. When constructing a reference with
  `from_manifest()`, omitting `label_node_paths` selects all recorded labels;
  explicitly passing `()` selects none.
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

See [Versioning and compatibility](versioning.md) for all version domains and
the fail-safe compatibility rules.

## RFC-8 draft projection boundary

`biomero_schema.rfc8.project_rfc8_v1_draft()` projects only the scientific
graph into the [OME-NGFF RFC-8 v1 draft](https://ngff.openmicroscopy.org/rfc/8/versions/v1-2026-08/index.html)
shape. Callers must provide explicit RFC paths; managed roots and provenance
never leak into the projected `ome` metadata. This is a design and test adapter,
not a production writer or a claim of conformance. RFC-8 is still evolving and
the deployed BIOMERO interchange profile remains NGFF 0.4 / Zarr v2.

## Example

```python
from biomero_schema.zarr import CanonicalZarrSource

source = CanonicalZarrSource.from_dict(payload)
wire_payload = source.to_dict()
map_annotation_values = source.to_annotation_values()
json_schema = CanonicalZarrSource.model_json_schema()
```

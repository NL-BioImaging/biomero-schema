# Import lifecycle

`ImportOptionsEnvelope` is the versioned request that accompanies an import
order. It keeps optional preprocessing/postprocessing operations separate from
OMERO registration settings.

## Schema 2 envelope

```json
{
  "schema": 2,
  "registration": {
    "schema": 1,
    "platePixelSource": "source",
    "plateLabelName": null
  },
  "operations": []
}
```

No operations means the established importer behavior. Legacy empty options
and flat schema-1 `ZarrImportOptions` are upcast to this shape, so deployments
that do not enable shallow storage remain unaffected.

## Shallow-Zarr operation

The `biomero.shallow-zarr` postprocess operation asks the importer to:

1. use the supplied ordered `CanonicalInputManifest` as the authoritative
   workflow-input snapshot;
2. compute identities for returned image nodes;
3. retain a full result whenever matching is missing, ambiguous, changed, or
   fails;
4. otherwise shallow the result into a managed collection before
   registering it with OMERO.

Identity worker parallelism is deployment configuration, not a client field.
This lets facilities balance import latency against CPU and storage costs.

This is the local shallowing path. A remotely shallowed result uses the
same operation with an additional `remoteReceipts` list. In that case the
importer validates the trusted receipt and associated report before reusing the
shallow collection; it does not repeat the completed pixel-identity pass.
See [Remote shallower contracts](remote-shallower-contracts.md) for the wire
format and the checks required at that boundary.

```json
{
  "kind": "biomero.shallow-zarr",
  "phase": "postprocess",
  "schema": 1,
  "canonicalInputs": {
    "schema": 1,
    "workflowId": "00000000-0000-0000-0000-000000000000",
    "exportTaskId": "00000000-0000-0000-0000-000000000001",
    "inputs": []
  },
  "failurePolicy": "keep-full",
  "importImageLabelViews": true,
  "importPlateLabelPreview": false,
  "plateLabelName": null
}
```

`remoteReceipts` defaults to an empty tuple in the Python model.
`ImportOptionsEnvelope.to_dict()` omits that field when empty, preserving the
existing serialized operation for local shallowing. Consumers should use
the envelope's `to_dict()` for the import-order wire payload rather than
serializing an operation independently.

Remote receipts require matching receipt-capable orchestration and importer
versions. Neither an empty receipt list nor installing this schema package
enables remote execution. Invalid receipts for already-shallowed data must not
be treated as permission to register an unverified result as full data.

## Registration controls

For a derived Plate, `platePixelSource: source` registers the source pixels as
the normal OMERO view while preserving the shallow collection as authority.
When an operator explicitly requests a Plate label preview,
`platePixelSource: label` and `plateLabelName` select one label node per Plate
image for the registered preview. No label array needs to be copied for that
view.

These controls are specific to the current OMERO Zarr registration workaround.
They can be retired or adapted when native OMERO label/collection support makes
them unnecessary.

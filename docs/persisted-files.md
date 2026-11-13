# Persisted files and version fields

BIOMERO components exchange state through files they leave next to the data.
Some of these files are contracts: several components read what another one
wrote, so their format is defined here as a Pydantic model and pinned by tests.
The others are internal state of a single component and are listed only so that
someone who finds one knows it is not a contract.

## Files with a shared model

| File or attribute | Model | Where | Written by | Read by |
| --- | --- | --- | --- | --- |
| `.biomero-shallow.json` | `ShallowManifest` | Root of a shallow Zarr result | BIOMERO.shallower | importer, scripts, BIOMERO.ZarrViewer, shallower |
| `biomero` key of the image nodes' `.zattrs` | `ShallowNodePointer` | Every image node of a shallow Zarr result | BIOMERO.shallower | shallower, its migration, BIOMERO.ZarrViewer |
| `.biomero-shallow-report.json` | `ShallowOperationReport` | Root of a Zarr returned by the remote helper | remote helper | shallower, importer |
| `.biomero-shallow-batch.json` | `ShallowBatchReport` | Returned-results directory | remote helper | BIOMERO core |
| `.biomero-input.json` | `CanonicalInput` | Temporary export Zarr, removed before registration | scripts | shallower, importer |
| `.biomero-canonical.json` | `CanonicalMarker` | Root of a canonical Zarr | importer | importer, scripts |
| `.biomero/<name>.canonical.json` | `CanonicalMarker` | Next to a Zarr indexed in place | importer | importer |
| `.biomero-import-storage.json` | `RemoteImportStorageRecord`, `ImporterShallowImportStorageRecord`, `ImporterFullImportStorageRecord` | Inside the root of the imported result Zarr | importer | scripts |

The sidecar location of the in-place canonical marker belongs to the importer
and may change; the content stays a `CanonicalMarker`.

## Files that are internal state

These have no shared model and are not contracts between components (where
another component touches one, for example the importer running the shallower's
recovery, it uses the owning component's code). Their format may change with
the component that owns them.

| File | Component | Purpose |
| --- | --- | --- |
| `.biomero-remote-attempt.json` | importer | A remote report that was not normalized, kept for diagnosis |
| `.<store>.biomero-prune-<token>/journal.json` | shallower | Rollback journal of a prune |
| `.<store>.biomero-lock`, `<name>.ome.zarr.lock` | shallower, importer | Locks |
| `.<store>.biomero-materialize-<token>` | shallower | Staging folder while reconstructing a shallow result |
| `.<store>.biomero-schema1-backup/` | shallower | Copies kept by the schema-1 migration |
| `.biomero-results-retrieved.json`, `.biomero-result-import.json` | scripts | Resume state of Import Results |

## The new models

### Import-storage record

`.biomero-import-storage.json` records what the importer actually did with a
result. It has three shapes, chosen by `location` and `storage`; each keeps
exactly the field set and key order the importer writes, and a field that
applies but has no value is `null`. The keys are snake_case and the version
field is `schema`; this differs from the camelCase contracts and is kept so
that existing files stay valid.

=== "Remote (`RemoteImportStorageRecord`)"

    ```json
    {"schema": 1, "workflow_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "storage": "shallow-zarr", "location": "remote", "decision_basis": "matched", "container": "helper:1", "tool_version": "1.0", "task_id": "t", "job_id": null, "report_sha256": "abc"}
    ```

=== "Importer, shallowed (`ImporterShallowImportStorageRecord`)"

    ```json
    {"schema": 1, "workflow_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "storage": "shallow-zarr", "location": "importer", "tool_version": "1.0", "decision_basis": "matched"}
    ```

=== "Importer, kept full (`ImporterFullImportStorageRecord`)"

    ```json
    {"schema": 1, "workflow_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "storage": "full-zarr", "location": "importer", "tool_version": "1.0", "reason": "pixels-differ"}
    ```

Use `parse_import_storage_record()` to read a file of unknown shape. The file
is absent for results imported before it existed; readers must treat that as
unknown provenance. `IMPORT_STORAGE_FILENAME` holds the file name.

### Canonical marker

`CanonicalMarker` is the commit marker of a canonical Zarr. It wraps the
`CanonicalZarrSource` of an Image, or the `CanonicalPlateSource` of a Plate.
Only a Plate source has `images` and no `sourceObjectType`; that is how the
union is resolved. The wrapper's version field is `markerSchema`, and the
wrapped source keeps its own `schema`. A marker whose `state` is not
`committed` is not valid. `CANONICAL_MARKER_NAME` holds the file name.

```json
{
  "markerSchema": 1,
  "source": {"schema": 1, "sourceObjectType": "Image", "...": "..."},
  "state": "committed"
}
```

The importer writes the file with sorted keys; key order is not part of the
format.

### Shallow node pointer

`ShallowNodePointer` is the `biomero` object in an image node's `.zattrs`
(`multiscales` is removed from that node). Its readers use it to find the
manifest from any node.

```json
{
  "format": "biomero-shallow-zarr",
  "manifest": ".biomero-shallow.json",
  "workflowId": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
}
```

The pointer has no `schema` field: `format` names the layout and the manifest
it points to carries the contract `schema`. Adding a field would be rejected by
older readers, so none is added. Only the current form is modelled. The
schema-1 pointer, which has `model: rfc8-shallow-copy` instead of `format`, is
read only by the BIOMERO.shallower migration, which rewrites it; the model
rejects it on purpose so an unmigrated store is never read as current.

## Version-field spellings

| Record | Field |
| --- | --- |
| All other models in this package | `schema` |
| Canonical marker wrapper | `markerSchema` |
| Import-storage record | `schema` (with snake_case keys) |
| `.zattrs` `biomero` pointer | none; `format` plus the manifest's `schema` |
| Internal state files | `schema` where present, but not a contract |

The spellings differ for historical reasons. Changing one would change files
that deployed components already read, so they stay. See
[Versioning and compatibility](versioning.md) for how a breaking change to any
of them must be introduced.

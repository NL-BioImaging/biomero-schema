# Import-storage record, canonical marker and Zarr pointer

Three persisted formats are read by more than one BIOMERO component. This
package defines each as a Pydantic model and pins it with tests built from the
files the writers produce, so that writers and readers share one definition.
All three are read as they are written today; no wire format changed when the
models were added.

For where each `.biomero*` file is stored on disk, which component writes and
reads it, and whether it is safe to delete, see the
[BIOMERO file reference](https://nl-bioimaging.github.io/NL-BIOMERO/master/developer/biomero-files.html)
in the NL-BIOMERO documentation. That page also lists the files that are
internal state of one component and not contracts.

## Import-storage record

`.biomero-import-storage.json` records what the importer actually did with a
result. It has three shapes, chosen by `location` and `storage`; each keeps
exactly the field set and key order the importer writes, and a field that
applies but has no value is `null`. The keys are snake_case and the version
field is `schema`, which is required; this differs from the camelCase
contracts and is kept so that existing files stay valid.

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

Importer releases before v1.5.0-beta.12 did not write `decision_basis` in the
remote and importer-shallow shapes, so it is optional in both models and reads
as `None` when absent. `job_id` is always written, as `null` when there is no
Slurm job.

Use `parse_import_storage_record()` to read a file of unknown shape; the union
type is `ImportStorageRecordUnion`. The file is absent for results imported
before it existed, and readers must treat that as unknown provenance.
`IMPORT_STORAGE_FILENAME` holds the file name.

## Canonical marker

`CanonicalMarker` is the commit marker of a canonical Zarr, stored as
`.biomero-canonical.json` in the store or as a sidecar file. It wraps the
`CanonicalZarrSource` of an Image, or the `CanonicalPlateSource` of a Plate.
Only a Plate source has `images` and no `sourceObjectType`; that is how the
union is resolved. The wrapper's version field is `markerSchema`, and the
wrapped source keeps its own `schema`. `markerSchema` and `state` are required,
and a marker whose `state` is not `committed` is not valid.
`CANONICAL_MARKER_NAME` holds the file name.

```json
{
  "markerSchema": 1,
  "source": {"schema": 1, "sourceObjectType": "Image", "...": "..."},
  "state": "committed"
}
```

The importer writes the file with sorted keys; key order is not part of the
format.

## Shallow node pointer

`ShallowNodePointer` is the `biomero` attribute of a shallow image node's NGFF
attributes (`.zattrs`, or `attributes.ome` in `zarr.json`); the node's
`multiscales` is removed. Readers use it to find the manifest from any node.
`format` and `manifest` have fixed values, so the model defaults them.

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
| `biomero` pointer | none; `format` plus the manifest's `schema` |

The spellings differ for historical reasons. Changing one would change files
that deployed components already read, so they stay. See
[Versioning and compatibility](versioning.md) for how a breaking change to any
of them must be introduced.

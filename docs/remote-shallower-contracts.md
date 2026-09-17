# Remote shallower contracts

`biomero_schema.shallower` defines the reports and receipts exchanged when
BIOMERO normalizes workflow results on Slurm before transferring them to the
importer. Remote normalization uses the same canonical-input snapshot and
shallow collection format as local normalization; it changes where that work
is performed, not the meaning of the stored result.

The schema package validates data structures only. It does not submit jobs,
read pixels, calculate file checksums, mutate Zarr stores, or access OMERO.
Workflow providers do not need to produce these records.

## Reports and authority

| Model | Stored record | Purpose |
| --- | --- | --- |
| `ShallowOperationReport` | `.biomero-shallow-report.json` inside a returned Zarr | Records one artifact's normalization decision, outcome, canonical inputs, helper provenance, and measurements. |
| `ShallowBatchReport` | `.biomero-shallow-batch.json` in the returned-results directory | Records completion of one helper invocation over that directory and collects receipts for normalized artifacts. This is not a workflow batching record. |
| `RemoteShallowReceipt` | Trusted orchestration data, forwarded in import options | Binds one normalized artifact to its report checksum, helper image/version, Slurm job, and tracking task. |

The constants `SHALLOW_OPERATION_REPORT` and `SHALLOW_BATCH_REPORT` provide
the filenames. The separate `.biomero-shallow.json` collection remains the
authority for the omitted image pixels and their canonical sources. A report
records what happened; it does not replace the collection or the trusted input
snapshot.

### Per-artifact outcome

`ShallowOperationReport` records `toolVersion`, an optional helper `image`,
`canonicalInputs`, the artifact name, a `decision`, a human-readable `reason`,
and a terminal `result`:

- `normalized`: the result contains a shallow `collection` and the decision
  must be `eligible`.
- `kept-full`: the full artifact is retained; no collection is included.
- `skipped`: the artifact is passed through without normalization; no
  collection is included.

The allowed decisions are `eligible`, `keep-full`, and `skip-passthrough`.
For normalized results, the report's artifact and workflow ID must match its
collection. `timings` contains named, non-negative durations in seconds.
Optional `bytesBefore` and `bytesAfter` record non-negative byte counts;
`slurmJobId` and `taskId` identify execution when available.

The initial report contract accepts `adapter: ngff-0.4-zarr-v2` and
`inputContract: 1` / `outputContract: 1`. These identify the helper's adapter
and input/output contract revisions, independently of its package version.

`ShallowBatchReport` has terminal `result: complete`. Its receipts describe
only successfully normalized artifacts, so an empty list is valid when all
artifacts were kept full or skipped. Batch completion does not mean every
artifact was made shallow.

## Trusted receipt

Every `RemoteShallowReceipt` field is required:

| Wire field | Meaning |
| --- | --- |
| `schema` | Receipt contract revision; currently `1`. |
| `image` | Helper container reference configured by the administrator. |
| `toolVersion` | Helper tool version used for normalization. |
| `reportSha256` | Lowercase, 64-character SHA-256 of the exact per-artifact report file bytes. It is not a pixel identity or a checksum of the whole Zarr store. |
| `artifactPath` | Relative, forward-slash path from the returned-results directory to the normalized Zarr. Absolute paths, parent traversal, and backslashes are rejected. |
| `slurmJobId` | Positive decimal Slurm job ID. |
| `taskId` | UUID of the tracked normalization task. |

An illustrative receipt is shown below. Actual checksums and identifiers must
come from the helper execution, and the image must match deployment
configuration.

```json
{
  "schema": 1,
  "image": "cellularimagingcf/biomero-shallower:0.1.0",
  "toolVersion": "0.1.0",
  "reportSha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "artifactPath": "results/segmentation.zarr",
  "slurmJobId": "123",
  "taskId": "00000000-0000-0000-0000-000000000001"
}
```

The importer receives the expected receipts through the
[`biomero.shallow-zarr` operation](import-lifecycle.md), not from an arbitrary
workflow-produced sidecar. Before accepting a remotely normalized result, the
consumer must bind it to exactly one expected receipt and verify the report
bytes, configured image/version, canonical-input snapshot, task/job identity,
and shallow collection. A checksum is not a signature: trust comes from the
orchestration hand-off, not from the presence of a report in a result directory.

When these checks succeed, the importer can reuse the completed normalization
without repeating pixel hashing. Invalid or missing provenance for an
already-shallowed result is an error; it cannot safely fall back to full pixels
that are no longer present. Full artifacts retained by the helper can still
follow the local preparation path.

## Compatibility and configuration

All three models require an explicit `schema: 1`. Missing or unknown versions
are rejected rather than silently interpreted as current records. Use
`from_dict()` and `to_dict()` for wire validation and serialization; use
`model_json_schema()` when integrating a non-Python consumer.

The import envelope remains schema 2 and the shallow operation remains schema
1. `remoteReceipts` is optional and omitted by
`ImportOptionsEnvelope.to_dict()` when empty. Local import payloads therefore
retain their established representation. Older readers do not understand the
new receipt field: upgrade the participating services before sending it.

Installing these models does not enable shallow storage or remote execution.
Feature flags, image acquisition, resource limits, and recovery procedures are
documented in the
[NL-BIOMERO remote shallower administration guide](https://nl-bioimaging.github.io/NL-BIOMERO/master/sysadmin/remote-shallower.html).
See [Versioning and compatibility](versioning.md) for the version domains and
the [Python API](api/shallower.md) for the model definitions.

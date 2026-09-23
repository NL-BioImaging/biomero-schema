# Versioning and compatibility

BIOMERO Schema contains several version domains. They must not be conflated.

| Version | Scope |
| --- | --- |
| package version | published Python distribution and dependency resolution |
| workflow `schema-version` | workflow descriptor language |
| contract `schema` | one cross-service wire record or envelope |
| NGFF version/profile | Zarr layout accepted by the deployed exporter, importer, and PixelBuffer |
| ISCC-BIO/IMAGEWALK revision | algorithm implementation that generated a pixel identity |

## Compatibility rules

- Additive changes should use optional fields with safe defaults.
- A breaking wire change requires a new integer contract `schema` and an
  explicit parser/upcaster in every consumer that accepts older persisted
  records.
- Readers must continue to accept events and OMERO annotations written by
  supported older deployments.
- Optional lifecycle operations default to absent; disabling the feature must
  preserve legacy import/export behavior.
- Unknown or unverifiable pixel identity is never permission to discard result
  pixels.

## Remote normalization compatibility

Remote operation reports, batch reports, and receipts each use contract schema
1 and require the version to be explicit. They are not legacy registration
options and are not upcast when their version is missing or unknown.

Adding `remoteReceipts` does not change the schema-2 import envelope or the
schema-1 shallow operation. When no receipts are present, the envelope writer
omits that field and preserves the local-operation wire representation. An
older reader may reject the new field because these models forbid unknown
fields; upgrade orchestration, helper, and importer to receipt-capable versions
before enabling remote normalization. The configured helper image and tool
version must agree with the receipt, independently of the schema package
version.

Shallow manifests may contain an image with no label nodes. This allows an
unchanged image result with no labels to reference its canonical pixels.

See [Remote shallower contracts](remote-shallower-contracts.md) for the report
formats and the checks performed by consuming services.

## OME-Zarr support window

The accepted interchange profile is a deployment capability, not whatever the
newest NGFF specification happens to define. BIOMERO currently depends on
Glencoe export/registration tooling and OMERO's Zarr PixelBuffer. Workflow
providers should target the profile BIOMERO supplies and return a compatible
base Image or Plate if the result must be visible in OMERO.

BIOMERO will advance this profile as Glencoe and OMERO release support for
newer NGFF versions. Providers are not expected to implement BIOMERO's internal
shallow manifest. The logical graph and operational bindings are separate so an
accepted RFC-8/Collections serializer can replace the private representation as
support matures.

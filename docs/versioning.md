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

## OME-Zarr support window

The accepted interchange profile is a deployment capability, not whatever the
newest NGFF specification happens to define. BIOMERO currently depends on
Glencoe export/registration tooling and OMERO's Zarr PixelBuffer. Workflow
providers should target the profile BIOMERO supplies and return a compatible
base Image or Plate if the result must be visible in OMERO.

BIOMERO will advance this profile as Glencoe and OMERO release support for
newer NGFF versions. Providers are not expected to implement BIOMERO's internal
shallow manifest; standard RFC-8/collection output can be adopted as support
matures.

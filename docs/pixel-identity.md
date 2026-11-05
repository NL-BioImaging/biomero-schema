# Resolution-specific pixel fingerprints

`PixelIdentity` records a resolution-specific pixel fingerprint using
[ISCC-BIO](https://github.com/bio-codes/iscc-bio). BIOMERO reads decoded numerical
planes from an existing NGFF pyramid level and supplies them to ISCC-BIO's
`generate_biocode(planes)` API. Upstream performs canonical row-major, big-endian
pixel encoding and hashing; planes follow IMAGEWALK Z → C → T order.

For original images BIOMERO selects the coarsest compatible stored level,
preserving every channel, Z slice and timepoint. Source and result must have
compatible dimensions, axes, dtype and coordinate transformations at both the
full and selected resolutions. A single-level image uses its full resolution.
Labels use full-resolution fingerprints independently of image comparison.

Equal Instance-Codes establish agreement of the selected canonical pixel byte
streams. Inferring unchanged full-resolution images from a smaller pyramid
level is **BIOMERO's deduplication policy**, not a full-resolution equality proof
or perceptual ISCC matching. Workflows must return internally consistent
pyramids. Unsupported or unmatched results remain full.

## What is calculated

| ISCC-BIO component | BIOMERO use |
| --- | --- |
| IMAGEWALK traversal and canonical pixel encoding | Selected-resolution planes |
| Instance-Code | Equality of canonical pixel bytes, with semantic guards |
| Data-Code and composite ISCC-SUM | Retained identifiers; similarity does not authorize removal |
| Raw file/store checksum | Not calculated for shallowing |
| Imagecode, perceptual Image-Code, Mixed-Code, rendered thumbnails | Not used |

An ISCC-SUM's meaning depends on its input byte stream. The composite returned
by the pixel API is not the raw-store checksum produced by the high-level file
API. Chunking and compression do not enter the decoded-pixel fingerprint.

## Current comparison record

Schema `2` uses the BIOMERO-specific profile `biomero-pixels-v1`.

| Wire field | Meaning |
| --- | --- |
| `schema`, `comparisonProfile` | Record version and comparison policy |
| `method` | `iscc-bio/imagewalk` algorithm family |
| `iscc`, `dataCode`, `instanceCode` | Pixel API composite, Data-Code and Instance-Code |
| `codeBits` | Bit length of each component code; currently 256 |
| `toolVersion`, `imagewalkRevision` | Generator versions for reproducibility |
| `nodePath`, `role` | Image/label node and role |
| `shape`, `dtype`, `axes`, `coordinateTransformations` | Full-resolution semantic guard |
| `datasetPath` | Selected array path; provenance, not an equality key |
| `comparisonShape`, `comparisonCoordinateTransformations` | Resolution actually fingerprinted |

Comparison requires current profiles, matching code lengths, Instance-Codes,
roles, full semantic guards and selected-resolution guards. Dataset/node path
spelling may differ. Data-Code similarity and the composite code do not decide
whether pixels may be omitted.

An old or missing profile is stale metadata. Consumers regenerate its single
current record from the same authoritative backing Zarr; they do not re-export,
copy or reimport the source, preserve a parallel legacy cache, or reinterpret
the old code as a new-profile fingerprint. Reading an older record exists only
to detect and refresh it. Source pixels and retained label stores remain intact.

## Source-linked decisions

The canonical locator and generation may exist without a `pixelIdentity`.
`imageMetadata` supplies cheap full-image semantics without requiring a hash.
This supports output interpretation without computing an unused identity.

Each shallow image binding records `decisionBasis`: `pixel-comparison`,
`ro-crate-output`, or `workflow-setting`. The comparison path requires a
measured `returnedPixelIdentity`; the source-linked paths leave it absent.
They reuse the known input as background, retain derived results and labels,
and make no claim that returned original pixels were measured or unchanged.
The canonical source's `canonicalPixelVerified` flag records prior source
verification; it is not a substitute for a current comparison fingerprint.

Shallow storage disabled always keeps full results. When enabled, usable
run-bound RO-Crate label outputs take precedence automatically. An independent
workflow setting supplies source-linked handling without usable declarations.
Otherwise pixel comparison runs. Neither metadata nor the setting overrides
the full-storage choice.

## Reproducibility and authority

The profile is BIOMERO policy; [IMAGEWALK IEP-0018](https://ieps.iscc.codes/iep-0018/)
is a draft upstream specification. Record both BIOMERO/helper and ISCC-BIO
versions. This does not claim certification of the full pipeline against ISCC.

Identity claims supplied by a workflow are not trusted comparison evidence.
Local shallowing computes the selected pixels; remote shallowing supplies the
[trusted receipt and report](remote-shallower-contracts.md). Canonical source
identity remains bound to the selected input's storage locator and generation.

# Pixel identity

`PixelIdentity` records the identity of one NGFF image or label node. BIOMERO
uses [ISCC-BIO](https://github.com/bio-codes/iscc-bio)'s IMAGEWALK method to
read decoded level-0 pixels in a deterministic plane order. This is the right
scope for answering “did the workflow change these image pixels?” because it
is independent of Zarr chunking, compression, added pyramid levels, labels,
and metadata edits.

It is not an ISCC TREEWALK checksum over the complete Zarr store. Such a store
checksum changes when labels or attributes are added and therefore cannot
decide whether the original image pixels stayed the same.

## Field reference

| JSON field | Meaning | Used for current equality? |
| --- | --- | --- |
| `schema` | Version of the BIOMERO `PixelIdentity` wire record. It is not an NGFF or ISCC version. | Validates the record |
| `method` | Identity algorithm family. Schema 1 requires `iscc-bio/imagewalk`. | Validates the record |
| `iscc` | Composite ISCC returned by ISCC-BIO. Useful as a portable content identifier and provenance claim. | No |
| `dataCode` | ISCC Data-Code component describing data similarity/content. It is retained for identification and future similarity use. | No |
| `instanceCode` | ISCC Instance-Code over IMAGEWALK's canonical decoded pixel byte stream. This is the exact pixel-code component. | **Yes** |
| `toolVersion` | Installed `iscc-bio` package version that produced the record. | Diagnostic only |
| `imagewalkRevision` | Exact IMAGEWALK implementation revision used by the generator. This makes an experimental implementation reproducible and auditable. | Diagnostic only |
| `nodePath` | Relative path of the image/label group within this Zarr store, for example `B/1/0`. | No; paths may change |
| `role` | Whether this node is an `image` or `label`. | **Yes** |
| `shape` | Level-0 array dimensions in axis order. | **Yes** |
| `dtype` | Level-0 decoded array data type, for example `uint16`. | **Yes** |
| `axes` | Ordered semantic axes corresponding one-to-one with `shape`. | **Yes** |
| `coordinateTransformations` | NGFF coordinate transformations that give the pixels their spatial meaning. | **Yes** |

!!! important "The code is a claim until BIOMERO verifies it"
    An identity embedded in metadata can be copied or left stale by a
    workflow. At the storage boundary BIOMERO recomputes the returned identity
    and compares it with the identity it recorded for the exact workflow
    input. The original is never deleted; only redundant pixels in that new
    workflow result are omitted after a successful comparison.

## Exact comparison predicate

In schema 1, two nodes are eligible for BIOMERO's “unchanged pixels” decision
only when all of the following values are equal:

```text
instanceCode
role
shape
dtype
axes
coordinateTransformations
```

`iscc`, `dataCode`, and `nodePath` are deliberately not equality keys. The
first two do not represent the exact comparison BIOMERO needs; the path is a
locator and can legitimately change between input and output stores.

Failure to compute an identity, a missing input match, ambiguity, or any guard
mismatch is fail-safe: the returned Zarr remains full.

## Example

```json
{
  "schema": 1,
  "method": "iscc-bio/imagewalk",
  "iscc": "ISCC:K4ABAOQM5UXJ2LU3VEQWTEUSR4R3KS5WH2RJGEYXM5G5PLCGSUS5D4A",
  "dataCode": "ISCC:GADRAOQM5UXJ2LU3VEQWTEUSR4R3K76D3R3JR6DXINBTCTJTQFTX3DY",
  "instanceCode": "ISCC:IADUXNR6UKJRGF3HJXL2YRUVEXI7BYADX6Z72BWSUK4QULFHH4U7N2Q",
  "toolVersion": "0.1.0",
  "imagewalkRevision": "iscc-bio/0.1.0@c536d7699b7d25592bfe5c91c947b749344b6914",
  "nodePath": "B/1/0",
  "role": "image",
  "shape": [2, 2008, 2008],
  "dtype": "uint16",
  "axes": ["c", "y", "x"],
  "coordinateTransformations": [
    {"type": "scale", "scale": [1, 0.345, 0.345]}
  ]
}
```

## Where identities live

The contract can appear inside `CanonicalZarrSource`, Plate image records,
workflow input snapshots, and `.biomero-shallow.json`. BIOMERO may also index
canonical source records in OMERO MapAnnotations. The schema does not require
mutating a provider's raw source Zarr.

ISCC maintainers recommend `attributes.iscc` on an NGFF Image group for a
portable embedded claim, as a sibling of `attributes.ome`. BIOMERO's current
managed-source record is intentionally richer because it also needs semantic
guards and storage provenance. A future stable ISCC-BIO/NGFF convention may
allow this representation to become smaller or more standard.

## Experimental points

- ISCC-BIO and IMAGEWALK are still young and their implementation metadata may
  evolve.
- Cross-format identity (for example, a LIF image and its canonical Zarr) is a
  valuable future capability but is not assumed by shallow normalization.
- Per-label identities are supported by the schema and are needed to distinguish
  inherited, changed, and new labels during chained workflows.
- BIOMERO records enough generator information to migrate or recompute codes if
  a future IMAGEWALK revision changes canonicalization.

See the upstream [IMAGEWALK specification](https://github.com/bio-codes/iscc-bio/blob/main/docs/imagewalk.md)
for algorithm details.

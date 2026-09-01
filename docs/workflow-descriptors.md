# Workflow descriptors

The workflow schema lets BIOMERO interpret FAIR workflow repositories without
owning their computational specification. It draws on BIAFLOWS, Cytomine,
NIST FAIR compute, and BILAYERS conventions.

## Top-level structure

A descriptor contains:

- identity and description;
- authors, institutions, and citations;
- an OCI, Docker, or Singularity container image;
- resource and execution configuration;
- typed inputs and outputs;
- the command-line template used to launch the container.

See [`tests/example_workflow.json`](https://github.com/NL-BioImaging/biomero-schema/blob/main/tests/example_workflow.json)
for a complete maintained example. The [workflow model API](api/workflow.md)
is the authoritative field reference.

## Zarr and Plate declarations

An image input declares Zarr by using one of the supported format spellings,
such as `zarr`, `omezarr`, `ome.zarr`, or `ome-zarr`. A Plate input uses the
`plate` image subtype. The model derives two useful flags:

- `requires-zarr` is true for a Zarr image input or a Plate input;
- `requires-plate` is true for a Plate input.

These declarations tell BIOMERO what representation to supply. They do not
require the workflow to understand BIOMERO's shallow-storage metadata.

## Output declarations drive UI suggestions

Output type and format declarations let clients suggest result handling:

- labeled image outputs can suggest ROI creation;
- measurement/CSV outputs can suggest OMERO tables;
- other file outputs can suggest file annotations.

Consumers should still treat each action as optional. A declared output may
not exist for every run, and handling a missing optional result should be a
no-op rather than an import failure.

## Supported OME-Zarr profile

Workflow providers should consume the OME-Zarr/NGFF profile supplied by the
BIOMERO deployment and emit a compatible base image/Plate when results must be
viewable through OMERO. The exact profile is constrained by the Glencoe
exporter and OMERO Zarr PixelBuffer versions deployed with BIOMERO, and will be
raised as those dependencies add newer NGFF support.

Native RFC-8 shallow output is an optional optimization, not a workflow
requirement. A portable workflow may simply return a full Zarr with unchanged
source pixels plus new labels; BIOMERO can verify and normalize that result at
its own storage boundary.

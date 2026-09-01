# Workflow descriptors

The workflow schema is BIOMERO's normalized internal representation. Workflow
providers normally publish an established external descriptor; the `biomero`
runtime detects that format, converts its supported fields, and validates the
result as a `WorkflowSchema`.

```text
external descriptor -> biomero adapter -> WorkflowSchema -> BIOMERO consumers
```

The conversion adapters belong to the
[`biomero` runtime](https://github.com/NL-BioImaging/biomero/blob/main/biomero/schema_parsers.py),
not this package. This distinction lets the Pydantic model remain a stable
contract between BIOMERO services while provider-facing specifications evolve
independently.

## Supported provider formats

| Input format | Detection and current conversion |
| --- | --- |
| [BILAYERS `config.yaml`](https://bilayers.org/understanding-config/) | Detected by `docker_image`. Converts the Docker image, `exec_function.cli_command`, citations, inputs, parameters, outputs, choices, formats, subtypes, file counts, and relevant server-managed flags. |
| [BIAFLOWS/Cytomine descriptor](https://neubias-wg5.github.io/creating_bia_workflow_and_adding_to_biaflows_instance.html) | Detected by `schema-version: cytomine-0.1` or the legacy descriptor shape. Converts the supported container, command, and non-Cytomine inputs. The current adapter does not derive explicit outputs, authorship, resource requirements, or citations from this legacy format. |
| Native BIOMERO descriptor | `schema-version: biomero-0.1` validates directly without conversion. This is mainly the normalized interchange between BIOMERO services, but an integration may emit it deliberately. |

CWL and OpenAPI are recognized but explicitly rejected as not yet supported.
Support means that the current adapter maps the fields listed above; it does
not imply complete implementation of every feature in the upstream format.

For new Zarr-to-Zarr or Plate-aware workflows, BILAYERS is the preferred
provider-facing route. Existing BIAFLOWS workflows remain supported without
requiring providers to rewrite them into a BIOMERO-owned specification.

## Top-level structure

A descriptor contains:

- identity and description;
- authors, institutions, and citations;
- an OCI, Docker, or Singularity container image;
- resource and execution configuration;
- typed inputs and outputs;
- the command-line template used to launch the container.

See [`tests/example_workflow.json`](https://github.com/NL-BioImaging/biomero-schema/blob/main/tests/example_workflow.json)
for a complete normalized example. The [workflow model API](api/workflow.md)
is the authoritative field reference after conversion. Provider-facing fields
should follow the linked BILAYERS or BIAFLOWS documentation.

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

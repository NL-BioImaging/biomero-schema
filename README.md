# BIOMERO Schema

This package contains Pydantic schemas shared by BIOMERO services. Schemas can
be exported as JSON Schema.

A CLI tool is included to validate and parse workflow descriptor files.

Two schema areas are kept separate:

* `biomero_schema.models` defines workflow descriptors.
* `biomero_schema.zarr` defines canonical Zarr source and pixel-identity
  interchange records. See [Zarr interchange contracts](docs/zarr-contracts.md).

The schema is a mix of:
* the [BiaFlows subset](https://neubias-wg5.github.io/creating_bia_workflow_and_adding_to_biaflows_instance.html#workflow_step3) of the (now deprecated) [original cytomine](https://github.com/cytomine/cytomine/blob/5f4f7cb3f90a244b8c95c064918fd6986a4de2cf/cytomine/utilities/descriptor_reader.py) schema
* the [new](https://github.com/cytomine/cytomine/blob/main/app-engine/src/main/resources/schemas/tasks/task.v0.json) cytomine App Engine task schema
* the [NIST fair-compute](https://github.com/usnistgov/fair-chain-compute-container/blob/master/schema/manifest.schema.json) schema
* the [Bilayers](https://bilayers.org/understanding-config/#defining-inputs) schema
* the [BIAFlows problem class list](https://neubias-wg5.github.io/problem_class_ground_truth.html#steps-section)


## Installation

`pixi` is used for installation and running some tasks. It's not strictly required, but recommended to [install pixi](https://pixi.sh/latest/installation/).

```bash
cd biomero_schema
pixi shell
```

Or use `pip install -e .` (or equivalent) in a virtual environment.

## Usage

### help

```bash
biomero-schema --help
```

## Predefined Tasks

Available `pixi` tasks.

```bash
pixi task list
```

### JSON Schema

The pydantic model is able to generate a JSON schema, which is printable with:

```bash
pixi run json-schema
# OR directly
biomero-schema schema
```

### Validate a JSON file against the schema

```bash
pixi run test-validate
```

### Parse a JSON file into a Pydantic representation

```bash
# Basic parsing with summary
pixi run test-parse

# Pretty print the full parsed object
pixi run test-pparse

# Output as JSON
pixi run test-jparse
```

## Files

- `src/biomero_schema/models.py` - Pydantic models for the schema
- `src/biomero_schema/cli.py` - CLI implementation
- `tests/example_workflow.json` - Example workflow file for testing

## Schema Structure

The schema defines a workflow with the following main components:

- **Basic Info**: name, description, schema-version
- **People & Organizations**: authors, institutions
- **Citations**: Required list of tool citations
- **Problem Class**: Optional [BIAFlows problem class](https://neubias-wg5.github.io/problem_class_ground_truth.html#steps-section)
- **Container**: container-image specification
- **Configuration**: Technical settings and resource requirements
- **Parameters**: inputs and outputs with type definitions
- **Command Line**: Template for execution

## Example

See `tests/example_workflow.json` for a complete example of a valid workflow definition.

## Schema Details

The following is json-ish psuedo-code that describes the schema:

```json
schema = 
{
  "name": "string",                      // Required. GitHub workflow repository name (without prefix). E.g. NucleiTracking-ImageJ
  "description": "string"                // Required. Description of workflow.
  "schema-version": "string"             // Required. Schema format identifier. Use the current schema version constant, e.g. "biomero-0.1".
  "authors":                             // Optional. Authors list.
    [
      {
        "name": "string",                // Required. Full name of author.
        "email": "string",               // Optional. Email address of author.
        "affiliations": "string[]"       // Optional. List of affiliations matching "id" of an institution in institutions list.
      }
    ],
  "institutions":                        // Optional. Institutions list.
    [
      {
        "id": "string",                  // Required. Unique institute identifier.
        "name": "string"                 // Optional. Name of the institution. Defaults to id.
      }
    ],
  "citations":                           // Required. List of citations for the tool. At least one citation required.
    [
      {
        "name": "string",                // Required. Name of the tool being cited.
        "doi": "string",                 // Optional. DOI number of the tool being cited. Defaults to empty string.
        "license": "string",             // Required. License of the tool being cited.
        "description": "string"          // Optional. Description of the tool being cited. Defaults to empty string.
      }
    ],
  // corresponding to: https://neubias-wg5.github.io/problem_class_ground_truth.html#steps-section
  "problem-class":                       // Optional. Biaflows problem class ("object-segmentation" | "pixel-classification" | "object-counting" | "object-detection" | "filament-tree-tracing" | "filament-networks-tracing" | "landmark-detection" | "particle-tracking" | "object-tracking").
  "container-image":                     // Required. Base container description.
    {
      "image": "string",                 // Required. Image to match the name of your workflow GitHub repository (lower case only). E.g. neubiaswg5/w_nucleitracking-imagej:1.0.0
      "type": "string",                  // Required. "oci" | "singularity" | "docker" (lower case only).
      "platforms": "string"[]            // Optional. Build-time multi-platform targets.
    },
  "configuration":                       // Optional. Technical configuration.
  {
    "input_folder": "string",            // Optional. Full path where the input folder must be mounted in the container. Defaults to "/inputs".
    "output_folder": "string",           // Optional. Full path where the output folder must be mounted in the container. Defaults to "/outputs".
    "resources":                         // Optional.
      {
        "networking": "boolean",         // Optional. Whether internet connection is needed. Defaults to False.
        "ram-min": "number",             // Optional. Minimum RAM in mebibytes (Mi). Defaults to 0.
        "cores-min": "number",           // Optional. Minimum number of CPU cores. Defaults to 1.
        "gpu": "boolean",                // Optional. GPU/accelerator required. Defaults to False.
        "cuda-requirements":             // Optional. GPU Cuda-related requirements.
          {
            "device-memory-min": "number", // Optional. Minimum device memory. Defaults to 0.
            "cuda-compute-capability": "string|string[]", // Optional: The cudaComputeCapability Schema; single min value or list of valid values. Defaults to None.
          },
        "cpuAVX": "boolean",             // Optional. Advanced Vector Extensions (AVX) CPU capability required. Defaults to False.
        "cpuAVX2": "boolean",            // Optional. Advanced Vector Extensions 2 (AVX2) CPU capability required. Defaults to False.
      }
  }
  "inputs":                              // Required. List of parameter descriptors.
    [
      {
        // references to "@id" get the value of "id" in lowercase
        // references to "@ID" get the value of "id" in uppercase
        "id": "string",                  // Required. Unique parameter identifier.
        "type": "string",                // Required. Data type of the parameter (Number|String|integer|float|boolean|string|file|image|array|measurement|executable).
        "name": "string",                // Optional. Human-readable display name appearing in BIAFLOWS UI (parameter dialog box). Defaults to "@id".
        "description": "string",         // Optional. Description of parameter. Context help in BIAFLOWS UI (parameter dialog box). Soft Defaults to "".
        "value-key": "string",           // Optional. Substitution key in CLI. Defaults to "[@ID]".
        "command-line-flag": "string",   // Optional. CLI flag. Defaults to "--@id".
        "default-value": "string|number|boolean", // Optional. Default value in BIAFLOWS UI (parameter dialog box). Soft Defaults to empty string.
        "optional": "boolean",           // Optional. If true, parameter not required. Soft Defaults to False.
        "set-by-server": "boolean",      // Optional. If true, parameter is server-assigned. Soft Defaults to False.
        "value-choices": "array",        // Optional. List of allowed values for this parameter.
        "value-choices-labels": "string[]", // Optional. Display labels for value-choices, index-aligned. When null, value is used as label.
        "mode": "string",                // Optional. UI display mode — "beginner" | "advanced". Advanced params are collapsed by default in the UI.
        "file-count": "string",          // Optional. For file-type inputs: "single" | "multiple".
        "format": "string|string[]",      // Optional. Type-specific. File extension(s) — see file/image/array sections below.
        "sub-type": "string|string[]",   // Optional. Type-specific. Image sub-type(s) — see image section below.
        "output-dir-set": "boolean",     // Optional. If true, this parameter specifies the output directory. Biomero will supply the data/out path.
        "file-attachment": "boolean",    // Optional. If true, this is a user-supplied OMERO file-attachment input (annotation ID). Biomero will download the file from OMERO and transfer it to the HPC at runtime, then inject the resolved path as the CLI argument.
      }
    ]
  "outputs":                           // Optional. List of output parameter descriptors.
    [
      {
        // references to "@id" get the value of "id" in lowercase
        // references to "@ID" get the value of "id" in uppercase
        "id": "string",                  // Required. Unique parameter identifier.
        "type": "string",                // Required. Data type of the parameter (Number|String|integer|float|boolean|string|file|image|array|measurement|executable).
        "name": "string",                // Optional. Human-readable display name appearing in BIAFLOWS UI (parameter dialog box). Defaults to "@id".
        "description": "string",         // Optional. Description of parameter. Context help in BIAFLOWS UI (parameter dialog box). Soft Defaults to "".
        "value-key": "string",           // Optional. Substitution key in CLI. Defaults to "[@ID]".
        "command-line-flag": "string",   // Optional. CLI flag. Defaults to "--@id".
        "default-value": "string|number|boolean", // Optional. Default value in BIAFLOWS UI (parameter dialog box). Soft Defaults to empty string.
        "optional": "boolean",           // Optional. If true, parameter not required. Soft Defaults to False.
        "set-by-server": "boolean",      // Optional. If true, parameter is server-assigned. Soft Defaults to False.
        "value-choices": "array",        // Optional. List of allowed values for this parameter.
        "value-choices-labels": "string[]", // Optional. Display labels for value-choices, index-aligned. When null, value is used as label.
        "mode": "string",                // Optional. UI display mode — "beginner" | "advanced". Advanced params are collapsed by default in the UI.
        "file-count": "string",          // Optional. For file-type outputs: "single" | "multiple".
        "format": "string|string[]",      // Optional. Type-specific. File extension(s) — see file/image/array sections below.
        "sub-type": "string|string[]",   // Optional. Type-specific. Image sub-type(s) — see image section below.
      }
    ]
  "command-line": "string"               // Required. e.g. "python wrapper.py CYTOMINE_HOST CYTOMINE_PUBLIC_KEY CYTOMINE_PRIVATE_KEY CYTOMINE_ID_PROJECT CYTOMINE_ID_SOFTWARE IJ_RADIUS IJ_THRESHOLD".
}

file =
{
  "format": "string"                    // Optional. Extension of the file type (e.g. .csv).
}

image =
{
  "sub-type": "string|string[]",        // Optional. Image type (grayscale|color|binary|labeled|class|plate). Can be a single value or list.
  "format": "string|string[]"           // Optional. Extension of the image type (tif|png|jpg|jpeg|tiff|ometiff|zarr|omezarr|ome.zarr|ome-zarr). Can be a single value or list.
}

array =
{
  "format": "string"                    // Optional. Extension of the file type (npy, npz)
}
```

## Computed Fields

The following fields are automatically computed from the schema and included in the JSON output:

- **`requires-zarr`** (`boolean`): `true` when any image input uses a ZARR format (`zarr`, `omezarr`, `ome.zarr`, `ome-zarr`) or has `plate` sub-type.
- **`requires-plate`** (`boolean`): `true` when any image input has `plate` sub-type.

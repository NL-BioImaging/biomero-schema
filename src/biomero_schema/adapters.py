# -*- coding: utf-8 -*-
# Copyright 2024 Torec Luik
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Workflow descriptor adapters for BIOMERO.

This module provides parsing of different workflow descriptor formats into
the biomero-schema format (our internal representation). The biomero-schema
is the primary format, with legacy formats adapted to fit this model.

Supported formats: native biomero-schema, BIAFLOWS/cytomine-0.1 and
BILAYERS ``config.yaml``. Moved here from ``biomero.schema_parsers`` so
descriptors can be converted without the BIOMERO runtime.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging

# biomero-schema is our internal representation
from biomero_schema.models import (
    BIOMERO_SCHEMA_VERSION,
    WorkflowSchema, Parameter, OutputParameter, ContainerImage, Author, Institution, Citation
)

logger = logging.getLogger(__name__)


class WorkflowDescriptorAdapter(ABC):
    """Abstract adapter to convert legacy formats to biomero-schema format."""

    @abstractmethod
    def adapt_to_biomero_schema(
        self, descriptor_data: Dict[str, Any]
    ) -> WorkflowSchema:
        """Convert raw descriptor data to validated biomero-schema format."""
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Return list of supported schema format identifiers."""
        pass


class BiomeroSchemaAdapter(WorkflowDescriptorAdapter):
    """Direct adapter for biomero-schema format (no conversion needed)."""

    def get_supported_formats(self) -> List[str]:
        return ["biomero-schema", "biomero-0.1"]

    def adapt_to_biomero_schema(
        self, descriptor_data: Dict[str, Any]
    ) -> WorkflowSchema:
        """Parse and validate biomero-schema descriptor directly."""
        # Direct Pydantic validation - this IS our internal representation
        return WorkflowSchema.model_validate(descriptor_data)


class BiaflowsSchemaAdapter(WorkflowDescriptorAdapter):
    """Adapter to convert BIAFLOWS/cytomine-0.1 format to biomero-schema."""

    def get_supported_formats(self) -> List[str]:
        return ["BIAFLOWS", "cytomine-0.1"]

    def adapt_to_biomero_schema(
        self, descriptor_data: Dict[str, Any]
    ) -> WorkflowSchema:
        """Convert BIAFLOWS descriptor to biomero-schema format."""

        # Convert container info
        container_info = descriptor_data.get("container-image", {})
        container_image = ContainerImage(
            image=container_info.get("image", ""),
            type=container_info.get("type", "singularity")
        )

        # Convert input parameters, filtering out cytomine-specific ones
        inputs = []
        for input_param in descriptor_data.get("inputs", []):
            if input_param.get("id", "").startswith("cytomine"):
                continue

            # Map BIAFLOWS types to biomero-schema types
            param_type = self._map_biaflows_type(
                input_param.get("type", "String"),
                input_param.get("default-value")
            )

            # Build command line info
            param_id = input_param.get("id", "")
            cmd_flag = input_param.get("command-line-flag", f"--{param_id}")
            cmd_flag = cmd_flag.replace("@id", param_id)
            value_key = input_param.get("value-key", f"@{param_id.upper()}")

            # Build the parameter data with alias names for Pydantic validation
            raw_default = input_param.get("default-value")
            param_data = {
                "id": param_id,
                "type": param_type,
                "name": input_param.get("name") or param_id,
                "description": input_param.get("description", ""),
                "value-key": value_key,  # Use alias name
                "command-line-flag": cmd_flag,  # Use alias name
                "default-value": raw_default,  # Alias
                "optional": input_param.get("optional", False),
                "set-by-server": input_param.get("set-by-server", False),
                "file-attachment": False,  # BIAFLOWS has no optional file-attachment inputs
                "value-choices": input_param.get("value-choices"),
            }
            
            # Create Parameter using model_validate with alias names
            input_param_obj = Parameter.model_validate(param_data)
            inputs.append(input_param_obj)

        # BIAFLOWS doesn't have explicit outputs, create empty list
        outputs = []

        # Create minimal author info (BIAFLOWS doesn't have this)
        authors = [Author(name="Unknown", email=None)]
        institutions = []
        citations = [Citation(
            name="Unknown Tool",
            license="Unknown",
            description="No citation information available"
        )]

        # Build the biomero-schema object
        biomero_descriptor = WorkflowSchema(
            schema_version=BIOMERO_SCHEMA_VERSION,  # Normalize to biomero-schema version
            name=descriptor_data.get("name", ""),
            description=descriptor_data.get("description"),
            command_line=descriptor_data.get("command-line"),
            container_image=container_image,
            inputs=inputs,
            outputs=outputs,
            authors=authors,
            institutions=institutions,
            citations=citations,
            problem_class=None,  # BIAFLOWS doesn't have this
            configuration=None   # BIAFLOWS doesn't have resource requirements
        )

        return biomero_descriptor

    def _map_biaflows_type(
        self, biaflows_type: str, default_value: Any = None
    ) -> str:
        """Map BIAFLOWS parameter types to biomero-schema types.
        
        BIAFLOWS Number type is converted to specific integer/float based on
        default value type. biomero-schema should never contain Number type.
        """
        if biaflows_type == 'Number':
            # Always convert Number type based on default value
            if default_value is not None and isinstance(default_value, float):
                return 'float'
            else:
                # Default to integer for Number type (most common case)
                return 'integer'
        
        # Direct mapping for other types
        type_mapping = {
            'String': 'string',
            'Boolean': 'boolean',
            'Integer': 'integer',
            'Float': 'float',
            'Domain': 'string',
            'ListDomain': 'string',
        }
        return type_mapping.get(biaflows_type, 'string')


class BilayersSchemaAdapter(WorkflowDescriptorAdapter):

    # Map bilayers types to biomero-schema types.
    # Types not listed here are passed through if valid, else fall back to 'string'.
    type_mapping = {
        'integer': 'integer',
        'float': 'float',
        'checkbox': 'boolean',
        'radio': 'string',
        'textbox': 'string',
        'text': 'string',
        'dropdown': 'string',
    }

    # Valid biomero-schema input types
    _valid_input_types = {
        "Number", "String", "integer", "float", "boolean",
        "string", "file", "image", "array", "measurement", "executable"
    }

    def get_supported_formats(self) -> List[str]:
        return ["bilayers"]

    def adapt_to_biomero_schema(
        self, descriptor_data: Dict[str, Any]
    ) -> WorkflowSchema:
        """Convert Bilayers descriptor to biomero-schema format."""

        # Convert container info
        container_info = descriptor_data.get("docker_image", {})
        # ignore container tag definition in descriptor
        container_image = ContainerImage(
            image=container_info.get('org') + '/' + container_info.get('name'),
            type=container_info.get("type", "docker")
        )

        # Convert input parameters (empty yaml lists may load as None)
        inputs = [self._map_bilayers(param) for param in
                  (descriptor_data.get("inputs") or []) + (descriptor_data.get("parameters") or [])]

        # Convert output parameters
        outputs = [self._map_bilayers(param, is_output=True) for param in
                   (descriptor_data.get("outputs") or [])]

        # Create citation information
        authors = [Author(name="Unknown", email=None)]
        institutions = []
        citations = [Citation(
            name=citation.get("name"),
            doi=citation.get("doi"),
            license=citation.get("license"),
            description=citation.get("description")
        ) for citation in (descriptor_data.get("citations") or [])]
        if len(citations) > 0:
            name = citations[0].name
            description = citations[0].description or ""
        else:
            # Fall back so validation reports the missing citations instead of failing here
            name = descriptor_data.get("algorithm_folder_name") or container_info.get("name", "")
            description = ""

        # Build the biomero-schema object
        biomero_descriptor = WorkflowSchema(
            schema_version="bilayers-1.0.0",  # Preserve source format for downstream detection
            name=name,
            description=description,
            command_line=descriptor_data.get("exec_function", {}).get("cli_command"),
            container_image=container_image,
            inputs=inputs,
            outputs=outputs,
            authors=authors,
            institutions=institutions,
            citations=citations,
            problem_class=None,  # Bilayers doesn't have this
            configuration=None,  # Bilayers doesn't have resource requirements
        )
        return biomero_descriptor

    def _map_bilayers(self, param, is_output=False):
        # Build command line info
        param_id = param.get("name", "")
        value_key = param_id.upper()

        # Map type: use explicit mapping, pass through if valid, else 'string'
        raw_type = param.get("type", "string")
        mapped_type = self.type_mapping.get(raw_type, raw_type)
        if mapped_type not in self._valid_input_types:
            mapped_type = "string"

        # Build the parameter data with alias names for Pydantic validation
        param_data = {
            "id": param_id,
            "type": mapped_type,
            "name": param.get("label", param_id),
            "description": param.get("description", param.get("label", "")),
            "value-key": value_key,  # Use alias name
            "command-line-flag": param.get("cli_tag", "").rstrip("=") or None,
            "optional": param.get("optional", False),
            # image inputs are handled by OMERO selection; output_dir_set is set by biomero server
            # file/array/measurement/executable are selected via attachment browser but path is server-injected
            "set-by-server": (
                raw_type in ("image", "file", "array", "measurement", "executable") and not is_output
            ) or param.get("output_dir_set", False),
            "output-dir-set": param.get("output_dir_set", False) or False,
            # file-attachment: user supplies an OMERO annotation ID; biomero transfers the file to HPC
            "file-attachment": (
                raw_type in ("file", "array", "measurement", "executable")
                and not is_output
            ),
            "mode": param.get("mode"),
        }

        default_value = param.get("default")
        if default_value is not None:
            param_data["default-value"] = default_value

        # Map bilayers 'options' list to value-choices and value-choices-labels
        options = param.get("options")
        if options:
            param_data["value-choices"] = [
                opt.get("value") for opt in options if "value" in opt
            ]
            labels = [opt.get("label") for opt in options if "value" in opt]
            # Only store labels when they differ from values (avoids redundant data)
            if any(str(lbl) != str(val) for lbl, val in zip(labels, param_data["value-choices"])):
                param_data["value-choices-labels"] = [str(lbl) if lbl is not None else None for lbl in labels]

        # Ensure the default value type is consistent with value-choices.
        # When all choices are integers the default MUST also be an int so
        # OMERO's scripts framework can match str(default) against the
        # stringified choices list.  We coerce unconditionally here (not just
        # when already a float) because Pydantic on older schema versions
        # re-coerces any int→float if int is absent from the Union — and
        # there is no way to prevent that without fixing the schema.
        # Fixing the schema (adding int to Union) is the real fix; this is
        # defence-in-depth that also pre-aligns the raw value before Pydantic.
        choices = param_data.get("value-choices", [])
        default = param_data.get("default-value")
        if choices and all(isinstance(c, int) for c in choices) and default is not None:
            try:
                coerced = int(default)
                # only coerce if it's a lossless conversion (e.g. 0.0→0 ok, 0.5 not)
                if coerced == default:
                    param_data["default-value"] = coerced
            except (ValueError, TypeError):
                pass

        param_format = param.get("format")
        if param_format:
            param_data["format"] = param_format

        file_count = param.get("file_count")
        if file_count:
            param_data["file-count"] = file_count

        subtype = param.get("subtype")
        if subtype:
            param_data["sub-type"] = subtype

        # Create Parameter using model_validate with alias names
        if is_output:
            param_obj = OutputParameter.model_validate(param_data)
        else:
            param_obj = Parameter.model_validate(param_data)

        return param_obj


def detect_schema_format(descriptor_data: Dict[str, Any]) -> str:
    """
    Auto-detect schema format from descriptor data.

    Args:
        descriptor_data: Raw descriptor dictionary

    Returns:
        Format identifier string

    Raises:
        ValueError: If format cannot be detected
    """
    # Check for CWL
    if "cwlVersion" in descriptor_data:
        raise ValueError("CWL format not yet supported")

    # Check for OpenAPI
    if ("$schema" in descriptor_data and
            "openapi" in descriptor_data["$schema"]):
        raise ValueError("OpenAPI format not yet supported")

    # Check schema-version field
    schema_version = descriptor_data.get("schema-version", "")
    if schema_version:
        if schema_version.startswith("cytomine"):
            return "BIAFLOWS"
        elif schema_version.startswith("biomero"):
            return "biomero-schema"
        elif (schema_version.startswith("bilayers")
              and "container-image" in descriptor_data):
            # Already converted by BilayersSchemaAdapter (keeps bilayers version)
            return "biomero-schema"

    # Fallback heuristics
    if "container-image" in descriptor_data and "inputs" in descriptor_data:
        # Looks like a workflow descriptor, assume cytomine format
        return "BIAFLOWS"

    if "docker_image" in descriptor_data:
        return "bilayers"

    keys = list(descriptor_data.keys())
    raise ValueError(
        f"Unable to detect schema format from descriptor: {keys}"
    )


class WorkflowDescriptorParser:
    """Main parser that converts any supported format to biomero-schema."""

    _adapters = {
        "BIAFLOWS": BiaflowsSchemaAdapter,
        "cytomine-0.1": BiaflowsSchemaAdapter,
        "biomero-schema": BiomeroSchemaAdapter,
        "biomero-0.1": BiomeroSchemaAdapter,
        "bilayers": BilayersSchemaAdapter,
    }

    @classmethod
    def parse_descriptor(
        cls, descriptor_data: Dict[str, Any], name: str = None
    ) -> WorkflowSchema:
        """
        Auto-detect format and parse descriptor to biomero-schema.

        Args:
            descriptor_data: Raw descriptor dictionary
            name: Optional name for logging purposes.

        Returns:
            Validated WorkflowSchema (biomero-schema format)

        Raises:
            ValueError: If format not supported or validation fails
        """
        schema_format = detect_schema_format(descriptor_data)

        adapter_class = cls._adapters.get(schema_format)
        if not adapter_class:
            available = list(cls._adapters.keys())
            raise ValueError(
                f"No adapter available for schema format '{schema_format}'. "
                f"Available: {available}"
            )

        adapter = adapter_class()
        name_str = f'"{name}" ' if name else ""
        logger.debug(
            f"Parsing {name_str}descriptor with format: {schema_format}"
        )

        # Convert to biomero-schema and validate with Pydantic
        return adapter.adapt_to_biomero_schema(descriptor_data)

    @classmethod
    def register_adapter(cls, schema_format: str, adapter_class: type):
        """Register a new adapter for a schema format."""
        cls._adapters[schema_format] = adapter_class


def parse_descriptor(descriptor_data: Dict[str, Any], name: str = None) -> WorkflowSchema:
    """Auto-detect format and parse a raw descriptor to biomero-schema."""
    return WorkflowDescriptorParser.parse_descriptor(descriptor_data, name=name)


# Backward compatibility alias (biomero.schema_parsers)
DescriptorParserFactory = WorkflowDescriptorParser

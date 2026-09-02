"""Versioned contracts for optional BIOMERO.importer lifecycle operations.

These models describe requests exchanged with the importer. They deliberately
do not implement storage mutation, conversion, or OMERO registration.
"""

from typing import Any, Literal, Mapping

from pydantic import Field, model_validator

from biomero_schema.zarr import (
    CanonicalInputManifest,
    ZarrContractModel,
    ZarrImportOptions,
)


IMPORT_OPTIONS_ENVELOPE_SCHEMA = 2
SHALLOW_ZARR_OPERATION = "biomero.shallow-zarr"


class ShallowZarrImportOperation(ZarrContractModel):
    """Request importer-owned shallow normalization before registration."""

    kind: Literal["biomero.shallow-zarr"] = SHALLOW_ZARR_OPERATION
    phase: Literal["postprocess"] = "postprocess"
    canonical_inputs: CanonicalInputManifest = Field(alias="canonicalInputs")
    failure_policy: Literal["keep-full"] = Field(
        default="keep-full",
        alias="failurePolicy",
    )
    import_image_label_views: bool = Field(
        default=True,
        alias="importImageLabelViews",
    )
    import_plate_label_preview: bool = Field(
        default=False,
        alias="importPlateLabelPreview",
    )
    plate_label_name: str | None = Field(
        default=None,
        alias="plateLabelName",
    )
    schema_version: Literal[1] = Field(default=1, alias="schema")

    @model_validator(mode="after")
    def validate_plate_preview(self) -> "ShallowZarrImportOperation":
        if self.plate_label_name and not self.import_plate_label_preview:
            raise ValueError(
                "plateLabelName requires importPlateLabelPreview=true"
            )
        if self.plate_label_name:
            if (
                self.plate_label_name in {".", ".."}
                or "/" in self.plate_label_name
                or "\\" in self.plate_label_name
            ):
                raise ValueError("plateLabelName must be one NGFF label name")
        return self


class ImportOptionsEnvelope(ZarrContractModel):
    """Importer registration controls plus ordered native operations."""

    registration: ZarrImportOptions = Field(
        default_factory=ZarrImportOptions,
    )
    operations: tuple[ShallowZarrImportOperation, ...] = Field(
        default_factory=tuple,
    )
    schema_version: Literal[2] = Field(
        default=IMPORT_OPTIONS_ENVELOPE_SCHEMA,
        alias="schema",
    )

    @model_validator(mode="after")
    def validate_unique_operations(self) -> "ImportOptionsEnvelope":
        kinds = [operation.kind for operation in self.operations]
        if len(kinds) != len(set(kinds)):
            raise ValueError("import lifecycle operation kinds must be unique")
        return self


def parse_import_options(
    value: ImportOptionsEnvelope | ZarrImportOptions | Mapping[str, Any] | None,
) -> ImportOptionsEnvelope:
    """Parse current options and upcast legacy flat registration options."""

    if isinstance(value, ImportOptionsEnvelope):
        return value
    if isinstance(value, ZarrImportOptions):
        return ImportOptionsEnvelope(registration=value)
    raw = dict(value or {})
    if not raw:
        return ImportOptionsEnvelope()
    if raw.get("schema", 1) == IMPORT_OPTIONS_ENVELOPE_SCHEMA:
        return ImportOptionsEnvelope.from_dict(raw)
    return ImportOptionsEnvelope(
        registration=ZarrImportOptions.from_dict(raw),
    )


__all__ = [
    "IMPORT_OPTIONS_ENVELOPE_SCHEMA",
    "SHALLOW_ZARR_OPERATION",
    "ImportOptionsEnvelope",
    "ShallowZarrImportOperation",
    "parse_import_options",
]

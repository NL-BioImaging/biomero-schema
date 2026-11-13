"""Versioned contracts for optional BIOMERO.importer lifecycle operations.

These models describe requests exchanged with the importer. They deliberately
do not implement storage mutation, conversion, or OMERO registration.
"""

from typing import Annotated, Any, Literal, Mapping, Union
from uuid import UUID

from pydantic import Discriminator, Field, Tag, TypeAdapter, model_validator
from biomero_schema.shallower import RemoteShallowReceipt

from biomero_schema.zarr import (
    CanonicalInputManifest,
    ZarrContractModel,
    ZarrImportOptions,
)


IMPORT_OPTIONS_ENVELOPE_SCHEMA = 2
SHALLOW_ZARR_OPERATION = "biomero.shallow-zarr"
IMPORT_STORAGE_FILENAME = ".biomero-import-storage.json"
IMPORT_STORAGE_SCHEMA = 1
IMPORT_STORAGE_SHALLOW = "shallow-zarr"
IMPORT_STORAGE_FULL = "full-zarr"
IMPORT_STORAGE_LOCATION_REMOTE = "remote"
IMPORT_STORAGE_LOCATION_IMPORTER = "importer"


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
    remote_receipts: tuple[RemoteShallowReceipt, ...] = Field(
        default_factory=tuple, alias="remoteReceipts",
    )

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

    def to_dict(self):
        value = super().to_dict()
        for operation in value["operations"]:
            if not operation.get("remoteReceipts"):
                operation.pop("remoteReceipts", None)
        return value

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


class ImportStorageModel(ZarrContractModel):
    """Base of the import-storage record shapes.

    Unlike the other contracts this file has always used snake_case keys and
    the key ``schema``; both are kept so that existing files stay readable.
    Fields are declared in the order the importer writes them.
    """

    schema_version: Literal[1] = Field(
        default=IMPORT_STORAGE_SCHEMA,
        alias="schema",
    )
    workflow_id: UUID
    storage: Literal["shallow-zarr", "full-zarr"]
    location: Literal["remote", "importer"]


class RemoteImportStorageRecord(ImportStorageModel):
    """Record written after the importer validated a remote shallowing report.

    Attributes:
        workflow_id (UUID): The workflow the result belongs to.
        storage (str): ``shallow-zarr``, or ``full-zarr`` when the remote
            helper kept the full result.
        location (str): Always ``remote``.
        decision_basis (str): The reason in the remote report.
        container (str): Remote helper image.
        tool_version (str): Shallower version of the remote helper.
        task_id (str): Tracking task of the remote helper.
        job_id (str | None): Slurm job of the helper, null when unknown.
        report_sha256 (str): Checksum of the remote report.
    """

    location: Literal["remote"] = IMPORT_STORAGE_LOCATION_REMOTE
    decision_basis: str
    container: str
    tool_version: str
    task_id: str
    job_id: str | None
    report_sha256: str


class ImporterShallowImportStorageRecord(ImportStorageModel):
    """Record written after the importer shallowed the result itself.

    Attributes:
        storage (str): Always ``shallow-zarr``.
        location (str): Always ``importer``.
        tool_version (str): Shallower version that handled the result.
        decision_basis (str): Why the result was shallowed.
    """

    storage: Literal["shallow-zarr"] = IMPORT_STORAGE_SHALLOW
    location: Literal["importer"] = IMPORT_STORAGE_LOCATION_IMPORTER
    tool_version: str
    decision_basis: str


class ImporterFullImportStorageRecord(ImportStorageModel):
    """Record written after the importer kept the full result.

    Attributes:
        storage (str): Always ``full-zarr``.
        location (str): Always ``importer``.
        tool_version (str): Shallower version that handled the result.
        reason (str): Why the full result was kept.
    """

    storage: Literal["full-zarr"] = IMPORT_STORAGE_FULL
    location: Literal["importer"] = IMPORT_STORAGE_LOCATION_IMPORTER
    tool_version: str
    reason: str


def _import_storage_record_kind(value: Any) -> str:
    """Pick the record shape the way the importer chooses it when writing.

    Args:
        value (Any): The raw record or an already built model.

    Returns:
        str: The tag of the matching union member.
    """
    if isinstance(value, Mapping):
        location, storage = value.get("location"), value.get("storage")
    else:
        location, storage = value.location, value.storage
    if location == IMPORT_STORAGE_LOCATION_REMOTE:
        return "remote"
    if storage == IMPORT_STORAGE_FULL:
        return "importer-full"
    return "importer-shallow"


ImportStorageRecord = Annotated[
    Union[
        Annotated[RemoteImportStorageRecord, Tag("remote")],
        Annotated[ImporterFullImportStorageRecord, Tag("importer-full")],
        Annotated[ImporterShallowImportStorageRecord, Tag("importer-shallow")],
    ],
    Discriminator(_import_storage_record_kind),
]

_IMPORT_STORAGE_RECORD_ADAPTER = TypeAdapter(ImportStorageRecord)


def parse_import_storage_record(
    value: Mapping[str, Any],
) -> (
    RemoteImportStorageRecord
    | ImporterFullImportStorageRecord
    | ImporterShallowImportStorageRecord
):
    """Validate the content of a ``.biomero-import-storage.json`` file.

    Args:
        value (Mapping[str, Any]): The parsed JSON object.

    Returns:
        RemoteImportStorageRecord | ImporterFullImportStorageRecord |
            ImporterShallowImportStorageRecord: The record of its shape.

    Raises:
        pydantic.ValidationError: If the value matches no shape.
    """
    return _IMPORT_STORAGE_RECORD_ADAPTER.validate_python(value)


__all__ = [
    "IMPORT_OPTIONS_ENVELOPE_SCHEMA",
    "IMPORT_STORAGE_FILENAME",
    "IMPORT_STORAGE_FULL",
    "IMPORT_STORAGE_LOCATION_IMPORTER",
    "IMPORT_STORAGE_LOCATION_REMOTE",
    "IMPORT_STORAGE_SCHEMA",
    "IMPORT_STORAGE_SHALLOW",
    "ImportStorageRecord",
    "ImporterFullImportStorageRecord",
    "ImporterShallowImportStorageRecord",
    "RemoteImportStorageRecord",
    "parse_import_storage_record",
    "SHALLOW_ZARR_OPERATION",
    "ImportOptionsEnvelope",
    "ShallowZarrImportOperation",
    "parse_import_options",
]

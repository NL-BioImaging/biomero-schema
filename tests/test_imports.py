import json
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from biomero_schema.imports import (
    IMPORT_STORAGE_FILENAME,
    IMPORT_STORAGE_SCHEMA,
    ImporterFullImportStorageRecord,
    ImporterShallowImportStorageRecord,
    ImportOptionsEnvelope,
    RemoteImportStorageRecord,
    ShallowZarrImportOperation,
    parse_import_options,
    parse_import_storage_record,
)
from biomero_schema.zarr import (
    CanonicalInputManifest,
    ZarrImportOptions,
)


def canonical_inputs():
    return CanonicalInputManifest(
        workflowId=uuid4(),
        exportTaskId=uuid4(),
        inputs=(),
    )


def test_empty_and_legacy_options_upcast_without_operations():
    assert parse_import_options(None) == ImportOptionsEnvelope()

    parsed = parse_import_options({
        "schema": 1,
        "platePixelSource": "label",
        "plateLabelName": "nuclei",
    })

    assert parsed.registration == ZarrImportOptions(
        platePixelSource="label",
        plateLabelName="nuclei",
    )
    assert parsed.operations == ()


def test_current_envelope_round_trips_with_shallow_operation():
    operation = ShallowZarrImportOperation(
        canonicalInputs=canonical_inputs(),
        importPlateLabelPreview=True,
        plateLabelName="nuclei",
    )
    original = ImportOptionsEnvelope(operations=(operation,))

    parsed = parse_import_options(original.to_dict())

    assert parsed == original
    assert parsed.to_dict()["schema"] == 2
    assert parsed.to_dict()["operations"][0]["kind"] == "biomero.shallow-zarr"


def test_plate_label_name_requires_enabled_preview():
    with pytest.raises(ValidationError, match="importPlateLabelPreview"):
        ShallowZarrImportOperation(
            canonicalInputs=canonical_inputs(),
            plateLabelName="nuclei",
        )


def test_operation_kinds_are_unique():
    operation = ShallowZarrImportOperation(
        canonicalInputs=canonical_inputs(),
    )
    with pytest.raises(ValidationError, match="must be unique"):
        ImportOptionsEnvelope(operations=(operation, operation))


def test_unknown_envelope_operation_is_rejected():
    with pytest.raises(ValidationError):
        parse_import_options({
            "schema": 2,
            "registration": {"schema": 1},
            "operations": [{
                "schema": 1,
                "kind": "unknown.operation",
                "phase": "postprocess",
                "canonicalInputs": canonical_inputs().to_dict(),
            }],
        })


# ---- import-storage record (.biomero-import-storage.json) ----------------

WORKFLOW_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

# Compact JSON as written by BIOMERO.importer's ImportStorageRecord.to_dict():
# the field set and the key order are part of the format.
REMOTE_RECORD_TEXT = (
    '{"schema": 1, "workflow_id": "' + WORKFLOW_ID + '", '
    '"storage": "shallow-zarr", "location": "remote", '
    '"decision_basis": "matched", "container": "helper:1", '
    '"tool_version": "1.0", "task_id": "t", "job_id": null, '
    '"report_sha256": "abc"}'
)
IMPORTER_SHALLOW_RECORD_TEXT = (
    '{"schema": 1, "workflow_id": "' + WORKFLOW_ID + '", '
    '"storage": "shallow-zarr", "location": "importer", '
    '"tool_version": "1.0", "decision_basis": "matched"}'
)
IMPORTER_FULL_RECORD_TEXT = (
    '{"schema": 1, "workflow_id": "' + WORKFLOW_ID + '", '
    '"storage": "full-zarr", "location": "importer", '
    '"tool_version": "1.0", "reason": "pixels-differ"}'
)

# Importer releases v1.5.0-beta.6 to beta.11 wrote no `decision_basis`.
REMOTE_RECORD_BETA_11_TEXT = (
    '{"schema": 1, "workflow_id": "' + WORKFLOW_ID + '", '
    '"storage": "shallow-zarr", "location": "remote", '
    '"container": "helper:1", "tool_version": "1.0", "task_id": "t", '
    '"job_id": "4711", "report_sha256": "abc"}'
)
IMPORTER_SHALLOW_RECORD_BETA_11_TEXT = (
    '{"schema": 1, "workflow_id": "' + WORKFLOW_ID + '", '
    '"storage": "shallow-zarr", "location": "importer", '
    '"tool_version": "1.0"}'
)


def test_import_storage_file_name_is_the_one_the_importer_uses():
    assert IMPORT_STORAGE_FILENAME == ".biomero-import-storage.json"


@pytest.mark.parametrize(
    "text, model",
    [
        (REMOTE_RECORD_TEXT, RemoteImportStorageRecord),
        (IMPORTER_SHALLOW_RECORD_TEXT, ImporterShallowImportStorageRecord),
        (IMPORTER_FULL_RECORD_TEXT, ImporterFullImportStorageRecord),
    ],
)
def test_import_storage_record_reproduces_the_written_file(text, model):
    record = parse_import_storage_record(json.loads(text))

    assert type(record) is model
    assert json.dumps(record.to_dict()) == text


@pytest.mark.parametrize(
    "text, model",
    [
        (REMOTE_RECORD_BETA_11_TEXT, RemoteImportStorageRecord),
        (IMPORTER_SHALLOW_RECORD_BETA_11_TEXT, ImporterShallowImportStorageRecord),
    ],
)
def test_import_storage_record_accepts_files_without_decision_basis(text, model):
    record = parse_import_storage_record(json.loads(text))

    assert type(record) is model
    assert record.decision_basis is None


def test_remote_record_may_report_a_full_result_and_a_job_id():
    wire = json.loads(REMOTE_RECORD_TEXT)
    wire.update(storage="full-zarr", job_id="4711")

    record = parse_import_storage_record(wire)

    assert isinstance(record, RemoteImportStorageRecord)
    assert record.storage == "full-zarr"
    assert record.job_id == "4711"
    assert record.workflow_id == UUID(WORKFLOW_ID)


@pytest.mark.parametrize(
    "change",
    [
        {"schema": 2},
        {"workflow_id": "not-a-uuid"},
        {"storage": "tiled"},
        {"location": "somewhere"},
        {"unexpected": True},
    ],
)
def test_import_storage_record_rejects_bad_values(change):
    wire = {**json.loads(IMPORTER_SHALLOW_RECORD_TEXT), **change}
    with pytest.raises(ValidationError):
        parse_import_storage_record(wire)


@pytest.mark.parametrize("missing", ["tool_version", "schema", "workflow_id"])
def test_import_storage_record_requires_the_common_fields(missing):
    wire = json.loads(IMPORTER_SHALLOW_RECORD_TEXT)
    del wire[missing]
    with pytest.raises(ValidationError):
        parse_import_storage_record(wire)


def test_remote_record_requires_job_id_to_be_written():
    # The importer always writes the key, as null when there is no Slurm job.
    wire = json.loads(REMOTE_RECORD_TEXT)
    del wire["job_id"]
    with pytest.raises(ValidationError):
        parse_import_storage_record(wire)


def test_import_storage_record_requires_the_fields_of_its_shape():
    wire = json.loads(IMPORTER_FULL_RECORD_TEXT)
    del wire["reason"]
    with pytest.raises(ValidationError):
        parse_import_storage_record(wire)

    # A shallow importer record is not a full one: `reason` is not its field.
    wire = json.loads(IMPORTER_SHALLOW_RECORD_TEXT)
    wire["reason"] = "x"
    with pytest.raises(ValidationError):
        parse_import_storage_record(wire)


@pytest.mark.parametrize("value", [None, [], 5, "text"])
def test_import_storage_record_rejects_non_mappings_with_a_validation_error(value):
    with pytest.raises(ValidationError):
        parse_import_storage_record(value)


def test_import_storage_record_accepts_a_built_model():
    record = ImporterFullImportStorageRecord(
        schema=IMPORT_STORAGE_SCHEMA,
        workflow_id=WORKFLOW_ID, tool_version="1.0", reason="pixels-differ"
    )

    assert parse_import_storage_record(record) == record
    assert json.dumps(record.to_dict()) == IMPORTER_FULL_RECORD_TEXT

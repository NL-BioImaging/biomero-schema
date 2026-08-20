from uuid import uuid4

import pytest
from pydantic import ValidationError

from biomero_schema.imports import (
    ImportOptionsEnvelope,
    ShallowZarrImportOperation,
    parse_import_options,
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

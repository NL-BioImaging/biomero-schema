"""Pin the persisted formats of the import-storage record, the canonical
marker and the ``.zattrs`` ``biomero`` pointer.

Every example is the exact content a writer produces today (copied from the
BIOMERO.importer and BIOMERO.shallower code and tests), so a failing test here
means a file written by a deployed component would no longer be accepted.
"""

import json
from uuid import UUID

import pytest
from pydantic import ValidationError

from biomero_schema import (
    CANONICAL_MARKER_NAME,
    IMPORT_STORAGE_FILENAME,
    SHALLOW_COLLECTION_MANIFEST,
    SHALLOW_FORMAT,
    CanonicalMarker,
    CanonicalPlateSource,
    CanonicalZarrSource,
    ImporterFullImportStorageRecord,
    ImporterShallowImportStorageRecord,
    PixelIdentity,
    RemoteImportStorageRecord,
    ShallowBindings,
    ShallowCollection,
    ShallowImageBinding,
    ShallowImageNode,
    ShallowManifest,
    ShallowNodePointer,
    parse_import_storage_record,
)

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

PIXEL_IDENTITY = {
    "schema": 1,
    "method": "iscc-bio/imagewalk",
    "nodePath": ".",
    "role": "image",
    "iscc": "ISCC:KPIXEL",
    "dataCode": "ISCC:GDATA",
    "instanceCode": "ISCC:IINSTANCE",
    "toolVersion": "0.1.0",
    "imagewalkRevision": "draft-2026-06",
    "shape": [1, 1, 1, 16, 16],
    "dtype": "uint16",
    "axes": ["t", "c", "z", "y", "x"],
    "coordinateTransformations": [],
}

# The `source_record` fixture of BIOMERO.importer's test_canonical_store.py,
# i.e. CanonicalZarrSource.to_dict() as the importer embeds it in the marker.
IMAGE_SOURCE = CanonicalZarrSource.from_dict({
    "schema": 1,
    "storageRoot": "group-5-data",
    "relativePath": "project/.processed/Image-3207.ome.zarr",
    "nodePath": ".",
    "sourceObjectType": "Image",
    "sourceObjectId": 3207,
    "sourceGeneration": 1,
    "interchangeProfile": "ngff-0.4-zarr-v2",
    "pixelIdentity": PIXEL_IDENTITY,
    "pixelIdentityOrigin": "raw",
    "canonicalPixelVerified": True,
    "storeIdentity": None,
}).to_dict()

# A Plate source has `images` and no `sourceObjectType`; each image carries a
# full CanonicalZarrSource of the same Plate.
PLATE_SOURCE = CanonicalPlateSource.from_dict({
    "schema": 1,
    "storageRoot": "group-5-data",
    "relativePath": "project/.processed/Plate-55.ome.zarr",
    "sourceObjectId": 55,
    "sourceGeneration": 1,
    "interchangeProfile": "ngff-0.4-zarr-v2",
    "storeIdentity": None,
    "images": [
        {
            "imageNodePath": path,
            "labels": [],
            "source": {
                **IMAGE_SOURCE,
                "relativePath": "project/.processed/Plate-55.ome.zarr",
                "nodePath": path,
                "sourceObjectType": "Plate",
                "sourceObjectId": 55,
                "pixelIdentity": {**PIXEL_IDENTITY, "nodePath": path},
            },
        }
        for path in ("A/1/0", "B/1/0")
    ],
}).to_dict()


def marker_text(source: dict) -> str:
    """Serialize a marker exactly as CanonicalStore.commit writes it."""
    marker = {"markerSchema": 1, "state": "committed", "source": source}
    return json.dumps(marker, indent=2, sort_keys=True)


def test_file_names_are_the_ones_the_writers_use() -> None:
    assert IMPORT_STORAGE_FILENAME == ".biomero-import-storage.json"
    assert CANONICAL_MARKER_NAME == ".biomero-canonical.json"


@pytest.mark.parametrize(
    "text, model",
    [
        (REMOTE_RECORD_TEXT, RemoteImportStorageRecord),
        (IMPORTER_SHALLOW_RECORD_TEXT, ImporterShallowImportStorageRecord),
        (IMPORTER_FULL_RECORD_TEXT, ImporterFullImportStorageRecord),
    ],
)
def test_import_storage_record_reproduces_the_written_file(text, model) -> None:
    record = parse_import_storage_record(json.loads(text))

    assert type(record) is model
    assert json.dumps(record.to_dict()) == text
    assert model.from_dict(json.loads(text)) == record


def test_remote_record_may_report_a_full_result_and_a_job_id() -> None:
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
def test_import_storage_record_rejects_bad_values(change) -> None:
    with pytest.raises(ValidationError):
        parse_import_storage_record({**json.loads(IMPORTER_SHALLOW_RECORD_TEXT), **change})


def test_import_storage_record_requires_the_fields_of_its_shape() -> None:
    wire = json.loads(IMPORTER_FULL_RECORD_TEXT)
    del wire["reason"]
    with pytest.raises(ValidationError):
        parse_import_storage_record(wire)

    # A shallow importer record is not a full one: `reason` is not its field.
    wire = json.loads(IMPORTER_SHALLOW_RECORD_TEXT)
    wire["reason"] = "x"
    with pytest.raises(ValidationError):
        parse_import_storage_record(wire)


def test_import_storage_record_keeps_snake_case_keys() -> None:
    record = ImporterShallowImportStorageRecord(
        workflow_id=WORKFLOW_ID, tool_version="1.0", decision_basis="matched"
    )

    assert list(record.to_dict()) == [
        "schema", "workflow_id", "storage", "location",
        "tool_version", "decision_basis",
    ]
    assert json.dumps(record.to_dict()) == IMPORTER_SHALLOW_RECORD_TEXT


@pytest.mark.parametrize(
    "source, source_model",
    [(IMAGE_SOURCE, CanonicalZarrSource), (PLATE_SOURCE, CanonicalPlateSource)],
)
def test_canonical_marker_reproduces_the_written_file(source, source_model) -> None:
    text = marker_text(source)

    marker = CanonicalMarker.from_dict(json.loads(text))

    assert isinstance(marker.source, source_model)
    assert marker_text(marker.to_dict()["source"]) == text
    assert json.dumps(marker.to_dict(), indent=2, sort_keys=True) == text


def test_canonical_marker_wire_keys() -> None:
    marker = CanonicalMarker(source=CanonicalZarrSource.from_dict(IMAGE_SOURCE))

    wire = marker.to_dict()

    assert wire["markerSchema"] == 1
    assert wire["state"] == "committed"
    assert set(wire) == {"markerSchema", "state", "source"}


@pytest.mark.parametrize(
    "change",
    [
        {"markerSchema": 2},
        {"state": "staging"},
        {"schema": 1},
        {"source": {}},
    ],
)
def test_canonical_marker_rejects_uncommitted_or_unknown_markers(change) -> None:
    wire = json.loads(marker_text(IMAGE_SOURCE))
    with pytest.raises(ValidationError):
        CanonicalMarker.from_dict({**wire, **change})


def test_canonical_marker_rejects_a_source_with_the_wrong_shape() -> None:
    # `images` with a `sourceObjectType` is an Image source with an extra field.
    wire = json.loads(marker_text(IMAGE_SOURCE))
    wire["source"]["images"] = []
    with pytest.raises(ValidationError):
        CanonicalMarker.from_dict(wire)


# The pointer exactly as BIOMERO.shallower's normalization writes it.
POINTER_WIRE = {
    "format": "biomero-shallow-zarr",
    "manifest": ".biomero-shallow.json",
    "workflowId": WORKFLOW_ID,
}


def test_shallow_node_pointer_reproduces_the_written_attribute() -> None:
    pointer = ShallowNodePointer.from_dict(POINTER_WIRE)

    assert pointer.workflow_id == UUID(WORKFLOW_ID)
    assert pointer.to_dict() == POINTER_WIRE
    assert list(pointer.to_dict()) == ["format", "manifest", "workflowId"]
    assert POINTER_WIRE["format"] == SHALLOW_FORMAT
    assert POINTER_WIRE["manifest"] == SHALLOW_COLLECTION_MANIFEST


def test_shallow_node_pointer_has_no_schema_field() -> None:
    # Adding `schema` would change the wire format; the manifest is versioned.
    with pytest.raises(ValidationError):
        ShallowNodePointer.from_dict({**POINTER_WIRE, "schema": 2})


def test_shallow_node_pointer_rejects_a_foreign_manifest_link() -> None:
    with pytest.raises(ValidationError):
        ShallowNodePointer.from_dict({**POINTER_WIRE, "manifest": "other.json"})


def test_schema_one_pointer_is_migration_only() -> None:
    # BIOMERO.shallower's migration still reads this older pointer itself and
    # rewrites it; this model must not accept an unmigrated schema-1 store.
    legacy = {
        "model": "rfc8-shallow-copy",
        "manifest": ".biomero-shallow.json",
        "workflowId": WORKFLOW_ID,
    }
    with pytest.raises(ValidationError):
        ShallowNodePointer.from_dict(legacy)


def test_shallow_node_pointer_from_manifest_matches_the_writer() -> None:
    manifest = ShallowManifest(
        workflow_id=WORKFLOW_ID,
        transfer_artifact="Image-3207.ome.zarr",
        interchange_profile="ngff-0.4-zarr-v2",
        collection=ShallowCollection(
            name="analysis result",
            images=(ShallowImageNode(id="image-0", name=".", node_path="."),),
        ),
        bindings=ShallowBindings(images=(ShallowImageBinding(
            node_id="image-0",
            source=CanonicalZarrSource.from_dict(IMAGE_SOURCE),
            returned_pixel_identity=PixelIdentity.from_dict(PIXEL_IDENTITY),
        ),)),
    )

    pointer = ShallowNodePointer.from_manifest(manifest)

    assert pointer.to_dict() == POINTER_WIRE

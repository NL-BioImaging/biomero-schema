"""Tests for cross-service Zarr contracts."""

import pytest
from pydantic import ValidationError
from uuid import UUID

from biomero_schema.zarr import (
    CANONICAL_SOURCE_NAMESPACE,
    CanonicalInput,
    CanonicalInputManifest,
    CanonicalZarrSource,
    PixelIdentity,
)


@pytest.fixture
def pixel_identity() -> PixelIdentity:
    return PixelIdentity(
        node_path=".",
        role="image",
        iscc_code="ISCC:KPIXEL",
        data_code="ISCC:GDATA",
        instance_code="ISCC:IINSTANCE",
        tool_version="0.1.0",
        imagewalk_revision="draft-2026-06",
        shape=(1, 2, 3, 64, 64),
        dtype="uint16",
        axes=("t", "c", "z", "y", "x"),
        coordinate_transformations=(
            {"type": "scale", "scale": [1, 1, 2, 0.5, 0.5]},
        ),
    )


@pytest.fixture
def canonical_source(pixel_identity: PixelIdentity) -> CanonicalZarrSource:
    return CanonicalZarrSource(
        storage_root="group-5-data",
        relative_path="project/.processed/Image-3207.g1.ome.zarr",
        node_path=".",
        source_object_type="Image",
        source_object_id=3207,
        source_generation=1,
        interchange_profile="ngff-0.4-zarr-v2",
        pixel_identity=pixel_identity,
        pixel_identity_origin="raw",
        canonical_pixel_verified=True,
        store_identity="ISCC:KSTORE",
    )


def test_wire_round_trip(canonical_source: CanonicalZarrSource) -> None:
    wire = canonical_source.to_dict()

    assert wire["sourceObjectId"] == 3207
    assert wire["pixelIdentity"]["nodePath"] == "."
    assert CanonicalZarrSource.from_dict(wire) == canonical_source


def test_annotation_round_trip(canonical_source: CanonicalZarrSource) -> None:
    values = canonical_source.to_annotation_values()

    assert CANONICAL_SOURCE_NAMESPACE == "biomero.zarr.source"
    assert values["canonicalPixelVerified"] == "true"
    assert CanonicalZarrSource.from_annotation_values(values) == canonical_source


def test_canonical_input_accepts_nested_wire_dict(
    canonical_source: CanonicalZarrSource,
) -> None:
    value = {
        "schema": 1,
        "ordinal": 0,
        "selectedObjectType": "Image",
        "selectedObjectId": 3207,
        "source": canonical_source.to_dict(),
    }

    assert CanonicalInput.from_dict(value).source == canonical_source


def test_canonical_input_manifest_is_json_portable(
    canonical_source: CanonicalZarrSource,
) -> None:
    canonical_input = CanonicalInput(
        ordinal=0,
        selected_object_type="Image",
        selected_object_id=3207,
        source=canonical_source,
    )
    manifest = CanonicalInputManifest(
        workflow_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        export_task_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        inputs=(canonical_input,),
    )

    wire = manifest.to_dict()

    assert wire["workflowId"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert wire["inputs"][0]["selectedObjectId"] == 3207
    assert CanonicalInputManifest.from_dict(wire) == manifest


def test_canonical_input_manifest_rejects_duplicate_ordinals(
    canonical_source: CanonicalZarrSource,
) -> None:
    item = CanonicalInput(
        ordinal=0,
        selected_object_type="Image",
        selected_object_id=3207,
        source=canonical_source,
    )

    with pytest.raises(ValidationError, match="ordinals must be unique"):
        CanonicalInputManifest(
            workflow_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            export_task_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            inputs=(item, item),
        )


@pytest.mark.parametrize(
    "relative_path",
    ["/data/source.ome.zarr", "../source.ome.zarr", "safe/../../escape.zarr"],
)
def test_rejects_unsafe_managed_paths(
    canonical_source: CanonicalZarrSource, relative_path: str
) -> None:
    value = canonical_source.to_dict()
    value["relativePath"] = relative_path

    with pytest.raises(ValidationError, match="relative managed path"):
        CanonicalZarrSource.from_dict(value)


def test_rejects_shape_axes_mismatch() -> None:
    with pytest.raises(ValidationError, match="same length"):
        PixelIdentity(
            node_path=".",
            role="image",
            iscc_code="ISCC:KPIXEL",
            data_code="ISCC:GDATA",
            instance_code="ISCC:IINSTANCE",
            tool_version="0.1.0",
            imagewalk_revision="draft-2026-06",
            shape=(64, 64),
            dtype="uint16",
            axes=("y",),
        )


def test_json_schema_is_independent_of_workflow_schema() -> None:
    schema = CanonicalZarrSource.model_json_schema()

    assert schema["title"] == "CanonicalZarrSource"
    assert "workflow" not in str(schema).lower()
    assert schema["properties"]["sourceObjectType"]["enum"] == ["Image", "Plate"]

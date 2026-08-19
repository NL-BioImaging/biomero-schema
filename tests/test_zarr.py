"""Tests for cross-service Zarr contracts."""

import pytest
from pydantic import ValidationError
from uuid import UUID

from biomero_schema.zarr import (
    CANONICAL_PLATE_IMAGE_NAMESPACE,
    CANONICAL_PLATE_LABEL_NAMESPACE,
    CANONICAL_SOURCE_NAMESPACE,
    CANONICAL_PLATE_SOURCE_NAMESPACE,
    SHALLOW_COLLECTION_NAMESPACE,
    CanonicalInput,
    CanonicalInputManifest,
    CanonicalPlateImage,
    CanonicalPlateImageRecord,
    CanonicalPlateIndex,
    CanonicalPlateLabelRecord,
    CanonicalPlateSource,
    CanonicalZarrSource,
    ManagedZarrNode,
    PixelIdentity,
    ShallowCollection,
    ShallowImageReference,
    ShallowPlateReference,
    ShallowZarrReference,
    ZarrImportOptions,
    ZarrLabelComponent,
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
        transfer_artifact="Image-3207.ome.zarr",
    )
    manifest = CanonicalInputManifest(
        workflow_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        export_task_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        inputs=(canonical_input,),
    )

    wire = manifest.to_dict()

    assert wire["workflowId"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert wire["inputs"][0]["selectedObjectId"] == 3207
    assert wire["inputs"][0]["transferArtifact"] == "Image-3207.ome.zarr"
    assert CanonicalInputManifest.from_dict(wire) == manifest


def test_canonical_input_accepts_legacy_payload_without_transfer_artifact(
    canonical_source: CanonicalZarrSource,
) -> None:
    item = CanonicalInput.from_dict({
        "ordinal": 0,
        "selectedObjectType": "Image",
        "selectedObjectId": 3207,
        "source": canonical_source.to_dict(),
        "schema": 1,
    })

    assert item.transfer_artifact is None
    assert item.labels == ()


def test_canonical_input_records_managed_label_snapshot(
    canonical_source: CanonicalZarrSource,
    pixel_identity: PixelIdentity,
) -> None:
    label_identity = pixel_identity.model_copy(update={
        "node_path": "labels/nuclei",
        "role": "label",
    })
    label = ZarrLabelComponent(
        logical_node_path="labels/nuclei",
        pixel_identity=label_identity,
        source=ManagedZarrNode(
            storage_root="import-mount-data",
            relative_path="Project A/.analyzed/first/result.zarr",
            node_path="labels/nuclei",
        ),
    )
    item = CanonicalInput(
        ordinal=0,
        selected_object_type="Image",
        selected_object_id=3207,
        source=canonical_source,
        transfer_artifact="result.zarr",
        labels=(label,),
    )

    assert CanonicalInput.from_dict(item.to_dict()) == item
    assert item.to_dict()["labels"][0]["logicalNodePath"] == "labels/nuclei"


def test_canonical_input_rejects_unmanaged_local_label(
    canonical_source: CanonicalZarrSource,
    pixel_identity: PixelIdentity,
) -> None:
    with pytest.raises(ValidationError, match="require managed sources"):
        CanonicalInput(
            ordinal=0,
            selected_object_type="Image",
            selected_object_id=3207,
            source=canonical_source,
            labels=(ZarrLabelComponent(
                logical_node_path="labels/nuclei",
                pixel_identity=pixel_identity.model_copy(update={
                    "node_path": "labels/nuclei",
                    "role": "label",
                }),
            ),),
        )


def test_canonical_plate_source_round_trips_with_per_image_identities(
    canonical_source: CanonicalZarrSource,
    pixel_identity: PixelIdentity,
) -> None:
    def plate_image(path: str, instance: str) -> CanonicalPlateImage:
        identity = pixel_identity.model_copy(update={
            "node_path": path,
            "instance_code": instance,
        })
        return CanonicalPlateImage(
            image_node_path=path,
            source=canonical_source.model_copy(update={
                "relative_path": ".processed/Plate-55.g1.ome.zarr",
                "node_path": path,
                "source_object_type": "Plate",
                "source_object_id": 55,
                "pixel_identity": identity,
            }),
        )

    plate = CanonicalPlateSource(
        storage_root="group-5-data",
        relative_path=".processed/Plate-55.g1.ome.zarr",
        source_object_id=55,
        source_generation=1,
        interchange_profile="ngff-0.4-zarr-v2",
        images=(
            plate_image("A/1/0", "ISCC:IA10"),
            plate_image("B/1/0", "ISCC:IB10"),
        ),
    )
    restored = CanonicalPlateSource.from_annotation_values(
        plate.to_annotation_values()
    )
    canonical_input = CanonicalInput(
        ordinal=0,
        selected_object_type="Plate",
        selected_object_id=55,
        transfer_artifact="plate.zarr",
        plate_source=plate,
    )

    assert CANONICAL_PLATE_SOURCE_NAMESPACE == "biomero.zarr.plate-source"
    assert restored == plate
    assert CanonicalInput.from_dict(canonical_input.to_dict()) == canonical_input


def test_canonical_plate_source_splits_into_bounded_omero_records(
    canonical_source: CanonicalZarrSource,
    pixel_identity: PixelIdentity,
) -> None:
    image_path = "A/1/0"
    plate_source = canonical_source.model_copy(update={
        "relative_path": ".processed/Plate-55.g1.ome.zarr",
        "node_path": image_path,
        "source_object_type": "Plate",
        "source_object_id": 55,
        "pixel_identity": pixel_identity.model_copy(update={
            "node_path": image_path,
        }),
    })
    label = ZarrLabelComponent(
        logical_node_path=f"{image_path}/labels/nuclei",
        pixel_identity=pixel_identity.model_copy(update={
            "node_path": f"{image_path}/labels/nuclei",
            "role": "label",
        }),
        source=ManagedZarrNode(
            storage_root="group-5-data",
            relative_path=".processed/Plate-55.g1.ome.zarr",
            node_path=f"{image_path}/labels/nuclei",
        ),
    )
    image = CanonicalPlateImage(
        image_node_path=image_path,
        source=plate_source,
        labels=(label,),
    )
    plate = CanonicalPlateSource(
        storage_root="group-5-data",
        relative_path=".processed/Plate-55.g1.ome.zarr",
        source_object_id=55,
        source_generation=1,
        interchange_profile="ngff-0.4-zarr-v2",
        images=(image,),
    )
    index = CanonicalPlateIndex.from_source(plate)
    image_record = CanonicalPlateImageRecord(
        source_object_id=55,
        source_generation=1,
        image=image.model_copy(update={"labels": ()}),
    )
    label_record = CanonicalPlateLabelRecord(
        source_object_id=55,
        source_generation=1,
        image_node_path=image_path,
        label=label,
    )

    assert CANONICAL_PLATE_IMAGE_NAMESPACE.endswith(".image")
    assert CANONICAL_PLATE_LABEL_NAMESPACE.endswith(".label")
    assert CanonicalPlateIndex.from_annotation_values(
        index.to_annotation_values()
    ) == index
    assert CanonicalPlateImageRecord.from_annotation_values(
        image_record.to_annotation_values()
    ) == image_record
    assert CanonicalPlateLabelRecord.from_annotation_values(
        label_record.to_annotation_values()
    ) == label_record


def test_plate_input_requires_matching_plate_source(
    canonical_source: CanonicalZarrSource,
) -> None:
    with pytest.raises(ValidationError, match="requires plateSource"):
        CanonicalInput(
            ordinal=0,
            selected_object_type="Plate",
            selected_object_id=55,
            source=canonical_source,
        )


def test_derived_plate_input_may_use_original_canonical_plate_source(
    canonical_source: CanonicalZarrSource,
    pixel_identity: PixelIdentity,
) -> None:
    source = canonical_source.model_copy(update={
        "relative_path": ".processed/Plate-55.g1.ome.zarr",
        "node_path": "A/1/0",
        "source_object_type": "Plate",
        "source_object_id": 55,
        "pixel_identity": pixel_identity.model_copy(update={
            "node_path": "A/1/0",
        }),
    })
    plate_source = CanonicalPlateSource(
        storage_root=source.storage_root,
        relative_path=source.relative_path,
        source_object_id=55,
        source_generation=source.source_generation,
        interchange_profile=source.interchange_profile,
        images=(CanonicalPlateImage(
            image_node_path="A/1/0",
            source=source,
        ),),
    )

    item = CanonicalInput(
        ordinal=0,
        selected_object_type="Plate",
        selected_object_id=901,
        plate_source=plate_source,
    )

    assert item.selected_object_id == 901
    assert item.plate_source.source_object_id == 55


def test_canonical_input_rejects_transfer_paths(
    canonical_source: CanonicalZarrSource,
) -> None:
    with pytest.raises(ValidationError, match="transferArtifact"):
        CanonicalInput(
            ordinal=0,
            selected_object_type="Image",
            selected_object_id=3207,
            source=canonical_source,
            transfer_artifact="data/in/Image-3207.ome.zarr",
        )


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


def test_shallow_collection_wire_round_trip(
    canonical_source: CanonicalZarrSource,
    pixel_identity: PixelIdentity,
) -> None:
    collection = ShallowCollection(
        workflow_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        transfer_artifact="Image-3207.ome.zarr",
        interchange_profile="ngff-0.4-zarr-v2",
        images=(ShallowImageReference(
            image_node_path=".",
            source=canonical_source,
            returned_pixel_identity=pixel_identity,
            label_node_paths=("labels/cells", "labels/nuclei"),
        ),),
    )

    wire = collection.to_dict()

    assert wire["model"] == "rfc8-shallow-copy"
    assert wire["images"][0]["source"]["sourceObjectId"] == 3207
    assert wire["images"][0]["labelNodePaths"] == [
        "labels/cells",
        "labels/nuclei",
    ]
    assert ShallowCollection.from_dict(wire) == collection


def test_shallow_collection_tracks_local_and_inherited_labels(
    canonical_source: CanonicalZarrSource,
    pixel_identity: PixelIdentity,
) -> None:
    nuclei_identity = pixel_identity.model_copy(update={
        "node_path": "labels/nuclei",
        "role": "label",
    })
    cells_identity = pixel_identity.model_copy(update={
        "node_path": "labels/cells",
        "role": "label",
        "instance_code": "ISCC:ICELLS",
    })
    collection = ShallowCollection(
        workflow_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        transfer_artifact="result.zarr",
        interchange_profile="ngff-0.4-zarr-v2",
        images=(ShallowImageReference(
            image_node_path=".",
            source=canonical_source,
            returned_pixel_identity=pixel_identity,
            label_node_paths=("labels/nuclei", "labels/cells"),
            label_components=(
                ZarrLabelComponent(
                    logical_node_path="labels/nuclei",
                    pixel_identity=nuclei_identity,
                    source=ManagedZarrNode(
                        storage_root="import-mount-data",
                        relative_path="Project A/.analyzed/first/result.zarr",
                        node_path="labels/nuclei",
                    ),
                ),
                ZarrLabelComponent(
                    logical_node_path="labels/cells",
                    pixel_identity=cells_identity,
                ),
            ),
        ),),
    )

    restored = ShallowCollection.from_dict(collection.to_dict())

    assert restored == collection
    assert restored.images[0].label_components[0].source is not None
    assert restored.images[0].label_components[1].source is None


def test_shallow_collection_requires_component_path_coverage(
    canonical_source: CanonicalZarrSource,
    pixel_identity: PixelIdentity,
) -> None:
    with pytest.raises(ValidationError, match="every labelNodePath"):
        ShallowImageReference(
            image_node_path=".",
            source=canonical_source,
            returned_pixel_identity=pixel_identity,
            label_node_paths=("labels/nuclei", "labels/cells"),
            label_components=(ZarrLabelComponent(
                logical_node_path="labels/nuclei",
                pixel_identity=pixel_identity.model_copy(update={
                    "node_path": "labels/nuclei",
                    "role": "label",
                }),
            ),),
        )


def test_shallow_reference_rejects_mismatched_identity_node(
    canonical_source: CanonicalZarrSource,
    pixel_identity: PixelIdentity,
) -> None:
    with pytest.raises(ValidationError, match="must equal imageNodePath"):
        ShallowImageReference(
            image_node_path="well/0",
            source=canonical_source,
            returned_pixel_identity=pixel_identity,
            label_node_paths=("well/0/labels/cells",),
        )


def test_shallow_zarr_reference_annotation_round_trip(
    canonical_source: CanonicalZarrSource,
    pixel_identity: PixelIdentity,
) -> None:
    collection = ShallowCollection(
        workflow_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        transfer_artifact="Image-3207.ome.zarr",
        interchange_profile="ngff-0.4-zarr-v2",
        images=(ShallowImageReference(
            image_node_path=".",
            source=canonical_source,
            returned_pixel_identity=pixel_identity,
            label_node_paths=("labels/cells",),
        ),),
    )
    reference = ShallowZarrReference.from_collection(
        collection,
        storage_root="import-mount-data",
        relative_path="Project A/.analyzed/run/result.zarr",
        image_node_path=".",
        label_node_paths=("labels/cells",),
    )

    values = reference.to_annotation_values()

    assert SHALLOW_COLLECTION_NAMESPACE == "biomero.zarr.shallow"
    assert values["labelNodePaths"] == '["labels/cells"]'
    assert ShallowZarrReference.from_annotation_values(values) == reference


def test_shallow_zarr_reference_requires_collection_membership(
    canonical_source: CanonicalZarrSource,
    pixel_identity: PixelIdentity,
) -> None:
    collection = ShallowCollection(
        workflow_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        transfer_artifact="Image-3207.ome.zarr",
        interchange_profile="ngff-0.4-zarr-v2",
        images=(ShallowImageReference(
            image_node_path=".",
            source=canonical_source,
            returned_pixel_identity=pixel_identity,
            label_node_paths=("labels/cells",),
        ),),
    )

    with pytest.raises(ValueError, match="labels must belong"):
        ShallowZarrReference.from_collection(
            collection,
            storage_root="import-mount-data",
            relative_path="Project A/.analyzed/run/result.zarr",
            image_node_path=".",
            label_node_paths=("labels/nuclei",),
        )


def test_json_schema_is_independent_of_workflow_schema() -> None:
    schema = CanonicalZarrSource.model_json_schema()

    assert schema["title"] == "CanonicalZarrSource"
    assert "workflow" not in str(schema).lower()
    assert schema["properties"]["sourceObjectType"]["enum"] == ["Image", "Plate"]


def test_shallow_plate_reference_round_trip(
    canonical_source: CanonicalZarrSource,
    pixel_identity: PixelIdentity,
) -> None:
    plate_source = canonical_source.model_copy(update={
        "source_object_type": "Plate",
        "source_object_id": 55,
        "node_path": "A/1/0",
        "relative_path": ".processed/Plate-55.g1.ome.zarr",
    })
    image_identity = pixel_identity.model_copy(update={
        "node_path": "A/1/0",
    })
    label_identity = pixel_identity.model_copy(update={
        "node_path": "A/1/0/labels/nuclei",
        "role": "label",
        "iscc_code": "ISCC:KLABEL",
        "data_code": "ISCC:DLABEL",
        "instance_code": "ISCC:ILABEL",
    })
    collection = ShallowCollection(
        workflow_id=UUID("00000000-0000-0000-0000-000000000123"),
        transfer_artifact="plate.ome.zarr",
        interchange_profile="ngff-0.4-zarr-v2",
        images=(ShallowImageReference(
            image_node_path="A/1/0",
            source=plate_source,
            returned_pixel_identity=image_identity,
            label_node_paths=("A/1/0/labels/nuclei",),
            label_components=(ZarrLabelComponent(
                logical_node_path="A/1/0/labels/nuclei",
                pixel_identity=label_identity,
            ),),
        ),),
    )

    reference = ShallowPlateReference.from_collection(
        collection,
        storage_root="group-3-data",
        relative_path=".analyzed/run/plate.ome.zarr",
    )

    assert reference.source_object_id == 55
    assert reference.image_node_count == 1
    assert ShallowPlateReference.from_annotation_values(
        reference.to_annotation_values()
    ) == reference


def test_zarr_import_options_require_label_for_label_plate() -> None:
    assert ZarrImportOptions().to_dict() == {
        "platePixelSource": "source",
        "plateLabelName": None,
        "schema": 1,
    }
    options = ZarrImportOptions(
        plate_pixel_source="label",
        plate_label_name="labels_nuclei",
    )
    assert ZarrImportOptions.from_dict(options.to_dict()) == options
    with pytest.raises(ValueError, match="plateLabelName"):
        ZarrImportOptions(plate_pixel_source="label")

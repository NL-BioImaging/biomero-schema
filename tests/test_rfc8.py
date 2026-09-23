"""Tests for the non-authoritative RFC-8 draft projection boundary."""

from uuid import UUID

import pytest

from biomero_schema.rfc8 import (
    RFC8_DRAFT_REVISION,
    Rfc8DraftPath,
    project_rfc8_v1_draft,
)
from biomero_schema.zarr import (
    CanonicalZarrSource,
    PixelIdentity,
    ShallowBindings,
    ShallowCollection,
    ShallowImageBinding,
    ShallowImageNode,
    ShallowLabelBinding,
    ShallowLabelNode,
    ShallowManifest,
    ZarrLabelComponent,
)


def _manifest() -> ShallowManifest:
    image_identity = PixelIdentity(
        node_path=".", role="image", iscc="ISCC:KIMAGE",
        data_code="ISCC:GIMAGE", instance_code="ISCC:IIMAGE",
        tool_version="0.2.0", imagewalk_revision="iscc-bio/0.2.0",
        shape=(1, 1, 8, 8), dtype="uint16", axes=("t", "c", "y", "x"),
    )
    label_identity = image_identity.model_copy(update={
        "node_path": "labels/cells", "role": "label",
        "iscc_code": "ISCC:KLABEL", "instance_code": "ISCC:ILABEL",
    })
    source = CanonicalZarrSource(
        storage_root="group-data", relative_path=".processed/source.zarr",
        node_path=".", source_object_type="Image", source_object_id=1,
        source_generation=1, interchange_profile="ngff-0.4-zarr-v2",
        pixel_identity=image_identity, pixel_identity_origin="raw",
        canonical_pixel_verified=True,
    )
    return ShallowManifest(
        workflow_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        transfer_artifact="result.zarr",
        interchange_profile="ngff-0.4-zarr-v2",
        collection=ShallowCollection(
            name="segmentation result",
            images=(ShallowImageNode(
                id="source-image", name="source", node_path=".",
            ),),
            labels=(ShallowLabelNode(
                id="cells", name="cells", node_path="labels/cells",
                source_image_id="source-image",
            ),),
        ),
        bindings=ShallowBindings(
            images=(ShallowImageBinding(
                node_id="source-image", source=source,
                returned_pixel_identity=image_identity,
            ),),
            labels=(ShallowLabelBinding(
                node_id="cells", component=ZarrLabelComponent(
                    logical_node_path="labels/cells",
                    pixel_identity=label_identity,
                ),
            ),),
        ),
    )


def _plate_manifest() -> ShallowManifest:
    def identity(node_path: str, suffix: str, role: str) -> PixelIdentity:
        return PixelIdentity(
            node_path=node_path,
            role=role,
            iscc=f"ISCC:K{suffix}",
            data_code=f"ISCC:G{suffix}",
            instance_code=f"ISCC:I{suffix}",
            tool_version="0.2.0",
            imagewalk_revision="iscc-bio/0.2.0",
            shape=(1, 1, 8, 8),
            dtype="uint16",
            axes=("t", "c", "y", "x"),
        )

    image_nodes = (
        ShallowImageNode(id="field-a1", name="A/1/0", nodePath="A/1/0"),
        ShallowImageNode(id="field-b1", name="B/1/0", nodePath="B/1/0"),
    )
    label_nodes = (
        ShallowLabelNode(
            id="cells-a1",
            name="cells A/1/0",
            nodePath="A/1/0/labels/cells",
            sourceImageId="field-a1",
        ),
        ShallowLabelNode(
            id="cells-b1",
            name="cells B/1/0",
            nodePath="B/1/0/labels/cells",
            sourceImageId="field-b1",
        ),
    )
    image_bindings = tuple(
        ShallowImageBinding(
            nodeId=node.node_id,
            source=CanonicalZarrSource(
                storageRoot="group-data",
                relativePath=".processed/Plate-7.ome.zarr",
                nodePath=node.node_path,
                sourceObjectType="Plate",
                sourceObjectId=7,
                sourceGeneration=3,
                interchangeProfile="ngff-0.4-zarr-v2",
                pixelIdentity=identity(
                    node.node_path, node.node_id.replace("-", "").upper(), "image"
                ),
                pixelIdentityOrigin="omero-pixels",
                canonicalPixelVerified=True,
            ),
            returnedPixelIdentity=identity(
                node.node_path, node.node_id.replace("-", "").upper(), "image"
            ),
        )
        for node in image_nodes
    )
    label_bindings = tuple(
        ShallowLabelBinding(
            nodeId=node.node_id,
            component=ZarrLabelComponent(
                logicalNodePath=node.node_path,
                pixelIdentity=identity(
                    node.node_path, node.node_id.replace("-", "").upper(), "label"
                ),
            ),
        )
        for node in label_nodes
    )
    return ShallowManifest(
        workflowId=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        transferArtifact="plate-result.zarr",
        interchangeProfile="ngff-0.4-zarr-v2",
        collection=ShallowCollection(
            name="Plate 7 segmentation result",
            images=image_nodes,
            labels=label_nodes,
        ),
        bindings=ShallowBindings(
            images=image_bindings,
            labels=label_bindings,
        ),
    )


def test_projects_only_portable_relationships_to_rfc8_v1_draft() -> None:
    projected = project_rfc8_v1_draft(
        _manifest(),
        ome_version="next",
        image_paths={
            "source-image": Rfc8DraftPath(
                type="zarr", path="../canonical/source.ome.zarr",
            ),
        },
        label_paths={
            "cells": Rfc8DraftPath(type="zarr", path="./labels/cells"),
        },
    )

    assert RFC8_DRAFT_REVISION == "v1-2026-08"
    assert projected == {
        "ome": {
            "version": "next",
            "type": "collection",
            "name": "segmentation result",
            "nodes": [
                {
                    "id": "source-image",
                    "name": "source",
                    "type": "multiscale",
                    "path": {
                        "type": "zarr",
                        "path": "../canonical/source.ome.zarr",
                    },
                },
                {
                    "id": "cells",
                    "name": "cells",
                    "type": "multiscale",
                    "path": {"type": "zarr", "path": "./labels/cells"},
                    "attributes": {
                        "labels": {"source": [{"id": "source-image"}]},
                    },
                },
            ],
        },
    }
    serialized = str(projected)
    assert "storageRoot" not in serialized
    assert "workflowId" not in serialized
    assert "ISCC:" not in serialized


def test_projects_plate_fields_and_labels_to_rfc8_v1_draft() -> None:
    projected = project_rfc8_v1_draft(
        _plate_manifest(),
        ome_version="next",
        image_paths={
            "field-a1": Rfc8DraftPath(
                type="zarr", path="../canonical-plate.ome.zarr/A/1/0",
            ),
            "field-b1": Rfc8DraftPath(
                type="zarr", path="../canonical-plate.ome.zarr/B/1/0",
            ),
        },
        label_paths={
            "cells-a1": Rfc8DraftPath(
                type="zarr", path="./A/1/0/labels/cells",
            ),
            "cells-b1": Rfc8DraftPath(
                type="zarr", path="./B/1/0/labels/cells",
            ),
        },
    )

    nodes = projected["ome"]["nodes"]
    assert [node["id"] for node in nodes] == [
        "field-a1", "field-b1", "cells-a1", "cells-b1",
    ]
    assert nodes[2]["attributes"]["labels"]["source"] == [
        {"id": "field-a1"},
    ]
    assert nodes[3]["attributes"]["labels"]["source"] == [
        {"id": "field-b1"},
    ]
    serialized = str(projected)
    assert "Plate-7" not in serialized
    assert "sourceObjectId" not in serialized
    assert "sourceGeneration" not in serialized
    assert "ISCC:" not in serialized


def test_rfc8_projection_requires_explicit_path_for_every_node() -> None:
    with pytest.raises(ValueError, match="one path per label node"):
        project_rfc8_v1_draft(
            _manifest(), ome_version="next",
            image_paths={
                "source-image": Rfc8DraftPath(
                    type="zarr", path="../source.ome.zarr",
                ),
            },
            label_paths={},
        )


def test_rfc8_projection_rejects_json_path_for_multiscale() -> None:
    with pytest.raises(ValueError, match="multiscale nodes"):
        project_rfc8_v1_draft(
            _manifest(), ome_version="next",
            image_paths={
                "source-image": Rfc8DraftPath(
                    type="json", path="../source.json",
                ),
            },
            label_paths={
                "cells": Rfc8DraftPath(type="zarr", path="./labels/cells"),
            },
        )

"""Projection boundary for the early OME-NGFF RFC-8 v1 draft.

RFC-8 v1 (2026-08) is not an adopted OME-NGFF specification.  This module
projects BIOMERO's format-independent collection graph into the draft shape so
that alignment can be tested without making draft metadata authoritative or
claiming that NGFF 0.4 / Zarr v2 stores are RFC-8 compliant.
"""

from typing import Literal, Mapping

from pydantic import Field

from .zarr import ShallowManifest, ZarrContractModel


RFC8_DRAFT_REVISION = "v1-2026-08"


class Rfc8DraftPath(ZarrContractModel):
    """A path accepted by the RFC-8 v1 draft projection."""

    type: Literal["zarr", "json"]
    path: str = Field(min_length=1)


def project_rfc8_v1_draft(
    manifest: ShallowManifest,
    *,
    ome_version: str,
    image_paths: Mapping[str, Rfc8DraftPath],
    label_paths: Mapping[str, Rfc8DraftPath],
) -> dict:
    """Project a shallow graph into the RFC-8 v1 draft collection shape.

    Callers provide paths because BIOMERO managed-storage bindings are not
    portable RFC paths.  Production writers must not use this projection until
    the selected NGFF profile and referenced stores support the accepted
    collections specification.
    """
    image_ids = {node.node_id for node in manifest.collection.images}
    label_ids = {node.node_id for node in manifest.collection.labels}
    if set(image_paths) != image_ids:
        raise ValueError("RFC-8 projection requires one path per image node")
    if set(label_paths) != label_ids:
        raise ValueError("RFC-8 projection requires one path per label node")
    paths = (*image_paths.values(), *label_paths.values())
    if any(path.type != "zarr" for path in paths):
        raise ValueError("multiscale nodes require RFC-8 zarr paths")

    nodes = []
    for image in manifest.collection.images:
        nodes.append({
            "id": image.node_id,
            "name": image.name,
            "type": "multiscale",
            "path": image_paths[image.node_id].to_dict(),
        })
    for label in manifest.collection.labels:
        nodes.append({
            "id": label.node_id,
            "name": label.name,
            "type": "multiscale",
            "path": label_paths[label.node_id].to_dict(),
            "attributes": {
                "labels": {
                    "source": [{"id": label.source_image_id}],
                },
            },
        })
    return {
        "ome": {
            "version": ome_version,
            "type": "collection",
            "name": manifest.collection.name,
            "nodes": nodes,
        },
    }


__all__ = [
    "RFC8_DRAFT_REVISION",
    "Rfc8DraftPath",
    "project_rfc8_v1_draft",
]

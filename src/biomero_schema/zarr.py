"""Cross-service schemas for BIOMERO-managed Zarr data.

These models describe portable records exchanged by BIOMERO services. They do
not implement canonical storage, OMERO access, workflow events, or Zarr I/O.
"""

import json
from pathlib import PurePosixPath
from typing import Any, Literal, Mapping
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CANONICAL_SOURCE_NAMESPACE = "biomero.zarr.source"
CANONICAL_SOURCE_SCHEMA = 1
PIXEL_IDENTITY_METHOD = "iscc-bio/imagewalk"


class ZarrContractModel(BaseModel):
    """Base configuration shared by the Zarr interchange contracts."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        validate_by_alias=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Return the stable camelCase wire representation."""
        return self.model_dump(by_alias=True, mode="json")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]):
        """Validate a wire representation."""
        return cls.model_validate(value)


def _validate_relative_path(value: str, *, allow_dot: bool) -> str:
    if not value or "\\" in value:
        raise ValueError(f"Expected a relative managed path, got {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Expected a relative managed path, got {value!r}")
    if not allow_dot and value == ".":
        raise ValueError(f"Expected a relative managed path, got {value!r}")
    return value


class PixelIdentity(ZarrContractModel):
    """ISCC-BIO identity and semantic guard for one NGFF image or label node."""

    node_path: str = Field(alias="nodePath")
    role: Literal["image", "label"]
    iscc_code: str = Field(alias="iscc", pattern=r"^ISCC:")
    data_code: str = Field(alias="dataCode", pattern=r"^ISCC:")
    instance_code: str = Field(alias="instanceCode", pattern=r"^ISCC:")
    tool_version: str = Field(alias="toolVersion", min_length=1)
    imagewalk_revision: str = Field(alias="imagewalkRevision", min_length=1)
    shape: tuple[int, ...] = Field(min_length=1)
    dtype: str = Field(min_length=1)
    axes: tuple[str, ...]
    coordinate_transformations: tuple[dict[str, Any], ...] = Field(
        default_factory=tuple,
        alias="coordinateTransformations",
    )
    method: Literal["iscc-bio/imagewalk"] = PIXEL_IDENTITY_METHOD
    schema_version: Literal[1] = Field(default=1, alias="schema")

    @property
    def schema(self) -> int:
        """Wire schema version (kept distinct from workflow schema versions)."""
        return self.schema_version

    @field_validator("node_path")
    @classmethod
    def validate_node_path(cls, value: str) -> str:
        return _validate_relative_path(value, allow_dot=True)

    @field_validator("shape")
    @classmethod
    def validate_shape(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(size < 1 for size in value):
            raise ValueError("shape must contain positive integer dimensions")
        return value

    @model_validator(mode="after")
    def validate_axes_match_shape(self) -> "PixelIdentity":
        if len(self.axes) != len(self.shape):
            raise ValueError("axes and shape must have the same length")
        return self


class CanonicalZarrSource(ZarrContractModel):
    """Managed locator for a verified canonical Zarr representation."""

    storage_root: str = Field(alias="storageRoot", min_length=1)
    relative_path: str = Field(alias="relativePath")
    node_path: str = Field(alias="nodePath")
    source_object_type: Literal["Image", "Plate"] = Field(
        alias="sourceObjectType"
    )
    source_object_id: int = Field(alias="sourceObjectId", gt=0)
    source_generation: int = Field(alias="sourceGeneration", gt=0)
    interchange_profile: str = Field(alias="interchangeProfile", min_length=1)
    pixel_identity: PixelIdentity = Field(alias="pixelIdentity")
    pixel_identity_origin: Literal[
        "raw", "omero-pixels", "canonical-bootstrap"
    ] = Field(alias="pixelIdentityOrigin")
    canonical_pixel_verified: bool = Field(alias="canonicalPixelVerified")
    store_identity: str | None = Field(
        default=None,
        alias="storeIdentity",
        pattern=r"^ISCC:",
    )
    schema_version: Literal[1] = Field(
        default=CANONICAL_SOURCE_SCHEMA,
        alias="schema",
    )

    @property
    def schema(self) -> int:
        """Wire schema version (kept distinct from workflow schema versions)."""
        return self.schema_version

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _validate_relative_path(value, allow_dot=False)

    @field_validator("node_path")
    @classmethod
    def validate_node_path(cls, value: str) -> str:
        return _validate_relative_path(value, allow_dot=True)

    @field_validator("canonical_pixel_verified", mode="before")
    @classmethod
    def validate_verified_flag(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            return value.lower() == "true"
        raise ValueError("canonicalPixelVerified must be true or false")

    def to_annotation_values(self) -> dict[str, str]:
        """Encode the record for an OMERO MapAnnotation value map."""
        values = {
            "schema": str(self.schema),
            "storageRoot": self.storage_root,
            "relativePath": self.relative_path,
            "nodePath": self.node_path,
            "sourceObjectType": self.source_object_type,
            "sourceObjectId": str(self.source_object_id),
            "sourceGeneration": str(self.source_generation),
            "interchangeProfile": self.interchange_profile,
            "pixelIdentity": json.dumps(
                self.pixel_identity.to_dict(), separators=(",", ":"), sort_keys=True
            ),
            "pixelIdentityOrigin": self.pixel_identity_origin,
            "canonicalPixelVerified": str(self.canonical_pixel_verified).lower(),
        }
        if self.store_identity is not None:
            values["storeIdentity"] = self.store_identity
        return values

    @classmethod
    def from_annotation_values(
        cls, values: Mapping[str, str]
    ) -> "CanonicalZarrSource":
        """Decode and validate an OMERO MapAnnotation value map."""
        verified = values["canonicalPixelVerified"].lower()
        if verified not in {"true", "false"}:
            raise ValueError("canonicalPixelVerified must be true or false")
        return cls(
            schema=int(values["schema"]),
            storage_root=values["storageRoot"],
            relative_path=values["relativePath"],
            node_path=values["nodePath"],
            source_object_type=values["sourceObjectType"],
            source_object_id=int(values["sourceObjectId"]),
            source_generation=int(values["sourceGeneration"]),
            interchange_profile=values["interchangeProfile"],
            pixel_identity=PixelIdentity.from_dict(
                json.loads(values["pixelIdentity"])
            ),
            pixel_identity_origin=values["pixelIdentityOrigin"],
            canonical_pixel_verified=verified == "true",
            store_identity=values.get("storeIdentity"),
        )


class CanonicalInput(ZarrContractModel):
    """One selected OMERO object and the exact canonical generation exported."""

    ordinal: int = Field(ge=0)
    selected_object_type: Literal["Image", "Plate"] = Field(
        alias="selectedObjectType"
    )
    selected_object_id: int = Field(alias="selectedObjectId", gt=0)
    source: CanonicalZarrSource
    transfer_artifact: str | None = Field(
        default=None,
        alias="transferArtifact",
    )
    schema_version: Literal[1] = Field(default=1, alias="schema")

    @property
    def schema(self) -> int:
        """Wire schema version (kept distinct from workflow schema versions)."""
        return self.schema_version

    @field_validator("transfer_artifact")
    @classmethod
    def validate_transfer_artifact(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value or value in {".", ".."} or "/" in value or "\\" in value:
            raise ValueError("transferArtifact must be one relative artifact name")
        return value


class CanonicalInputManifest(ZarrContractModel):
    """Recovery manifest for the canonical inputs exported for one workflow."""

    workflow_id: UUID = Field(alias="workflowId")
    export_task_id: UUID = Field(alias="exportTaskId")
    inputs: tuple[CanonicalInput, ...] = Field(default_factory=tuple)
    schema_version: Literal[1] = Field(default=1, alias="schema")

    @property
    def schema(self) -> int:
        """Wire schema version (kept distinct from workflow schema versions)."""
        return self.schema_version

    @model_validator(mode="after")
    def validate_unique_ordinals(self) -> "CanonicalInputManifest":
        ordinals = [item.ordinal for item in self.inputs]
        if len(ordinals) != len(set(ordinals)):
            raise ValueError("canonical input ordinals must be unique")
        return self


__all__ = [
    "CANONICAL_SOURCE_NAMESPACE",
    "CANONICAL_SOURCE_SCHEMA",
    "PIXEL_IDENTITY_METHOD",
    "CanonicalInput",
    "CanonicalInputManifest",
    "CanonicalZarrSource",
    "PixelIdentity",
]

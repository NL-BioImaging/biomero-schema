"""Biomero schema package."""
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("biomero-schema")
except PackageNotFoundError:
    __version__ = "unknown"

from biomero_schema.models import BIOMERO_SCHEMA_VERSION
from biomero_schema.zarr import (
    CANONICAL_SOURCE_NAMESPACE,
    CANONICAL_SOURCE_SCHEMA,
    PIXEL_IDENTITY_METHOD,
    SHALLOW_COLLECTION_MANIFEST,
    SHALLOW_COLLECTION_NAMESPACE,
    CanonicalInput,
    CanonicalInputManifest,
    CanonicalZarrSource,
    ManagedZarrNode,
    PixelIdentity,
    ShallowCollection,
    ShallowImageReference,
    ShallowZarrReference,
    ZarrLabelComponent,
)

__all__ = [
    "__version__",
    "BIOMERO_SCHEMA_VERSION",
    "CANONICAL_SOURCE_NAMESPACE",
    "CANONICAL_SOURCE_SCHEMA",
    "PIXEL_IDENTITY_METHOD",
    "SHALLOW_COLLECTION_MANIFEST",
    "SHALLOW_COLLECTION_NAMESPACE",
    "CanonicalInput",
    "CanonicalInputManifest",
    "CanonicalZarrSource",
    "ManagedZarrNode",
    "PixelIdentity",
    "ShallowCollection",
    "ShallowImageReference",
    "ShallowZarrReference",
    "ZarrLabelComponent",
]

"""Biomero schema package."""
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("biomero-schema")
except PackageNotFoundError:
    __version__ = "unknown"

from biomero_schema.models import BIOMERO_SCHEMA_VERSION
from biomero_schema.imports import (
    IMPORT_OPTIONS_ENVELOPE_SCHEMA,
    SHALLOW_ZARR_OPERATION,
    ImportOptionsEnvelope,
    ShallowZarrImportOperation,
    parse_import_options,
)
from biomero_schema.zarr import (
    CANONICAL_PLATE_IMAGE_NAMESPACE,
    CANONICAL_PLATE_LABEL_NAMESPACE,
    CANONICAL_SOURCE_NAMESPACE,
    CANONICAL_SOURCE_SCHEMA,
    CANONICAL_PLATE_SOURCE_NAMESPACE,
    PIXEL_IDENTITY_METHOD,
    SHALLOW_COLLECTION_MANIFEST,
    SHALLOW_COLLECTION_NAMESPACE,
    TRANSFER_INPUT_MARKER,
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

__all__ = [
    "__version__",
    "BIOMERO_SCHEMA_VERSION",
    "IMPORT_OPTIONS_ENVELOPE_SCHEMA",
    "SHALLOW_ZARR_OPERATION",
    "ImportOptionsEnvelope",
    "ShallowZarrImportOperation",
    "parse_import_options",
    "CANONICAL_PLATE_IMAGE_NAMESPACE",
    "CANONICAL_PLATE_LABEL_NAMESPACE",
    "CANONICAL_SOURCE_NAMESPACE",
    "CANONICAL_SOURCE_SCHEMA",
    "CANONICAL_PLATE_SOURCE_NAMESPACE",
    "PIXEL_IDENTITY_METHOD",
    "SHALLOW_COLLECTION_MANIFEST",
    "SHALLOW_COLLECTION_NAMESPACE",
    "TRANSFER_INPUT_MARKER",
    "CanonicalInput",
    "CanonicalInputManifest",
    "CanonicalPlateImage",
    "CanonicalPlateImageRecord",
    "CanonicalPlateIndex",
    "CanonicalPlateLabelRecord",
    "CanonicalPlateSource",
    "CanonicalZarrSource",
    "ManagedZarrNode",
    "PixelIdentity",
    "ShallowCollection",
    "ShallowImageReference",
    "ShallowPlateReference",
    "ShallowZarrReference",
    "ZarrImportOptions",
    "ZarrLabelComponent",
]

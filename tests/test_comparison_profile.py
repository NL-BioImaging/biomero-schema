"""Versioned comparison evidence must distinguish measured and reused pixels."""
import pytest
from pydantic import ValidationError

from biomero_schema.zarr import PixelIdentity, CanonicalZarrSource, ShallowImageBinding


def identity(**extra):
    return PixelIdentity(node_path='.', role='image', iscc_code='ISCC:SUM',
                         data_code='ISCC:DATA', instance_code='ISCC:INSTANCE',
                         tool_version='0.2.0', imagewalk_revision='IEP-0018',
                         shape=(2, 3, 16, 16), dtype='uint16',
                         axes=('c', 'z', 'y', 'x'), **extra)


def test_old_or_missing_profile_is_stale_without_reinterpreting_codes():
    assert not identity(schema=1).is_current_profile
    assert not identity().is_current_profile
    assert not identity(comparison_profile='old').is_current_profile


def test_current_profile_records_resolution_but_preserves_full_semantics():
    value = identity(comparison_profile='biomero-pixels-v1', dataset_path='s2',
                     comparison_shape=(2, 3, 4, 4),
                     comparison_coordinate_transformations=(
                         {'type': 'scale', 'scale': [1, 1, 4, 4]},))
    assert value.is_current_profile
    assert value.schema == 2
    assert value.shape == (2, 3, 16, 16)
    assert PixelIdentity.from_dict(value.to_dict()) == value


def test_profile_cannot_silently_drop_channels_or_z():
    with pytest.raises(ValidationError):
        identity(comparison_profile='biomero-pixels-v1', dataset_path='s2',
                 comparison_shape=(1, 1, 4, 4))


def test_source_link_has_no_fabricated_identity():
    source = CanonicalZarrSource(storage_root='data', relative_path='input.zarr',
                                node_path='.', source_object_type='Image',
                                source_object_id=1, source_generation=1,
                                interchange_profile='ngff-0.4-zarr-v2',
                                pixel_identity_origin='canonical-bootstrap',
                                canonical_pixel_verified=False)
    assert CanonicalZarrSource.from_annotation_values(source.to_annotation_values()) == source
    value = ShallowImageBinding(node_id='image-0', source=source,
                                decision_basis='ro-crate-output')
    assert value.returned_pixel_identity is None
    with pytest.raises(ValidationError):
        ShallowImageBinding(node_id='image-0', source=source)

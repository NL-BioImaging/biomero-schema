from uuid import uuid4

import pytest

from biomero_schema.shallower import RemoteShallowReceipt
from biomero_schema.imports import ImportOptionsEnvelope, ShallowZarrImportOperation
from biomero_schema.zarr import CanonicalInputManifest


def receipt():
    return dict(schema=1, image='helper:0.1.0', toolVersion='0.1.0',
                reportSha256='a' * 64, artifactPath='result.zarr',
                slurmJobId='123', taskId=str(uuid4()))


@pytest.mark.parametrize('version', [None, 2])
def test_remote_receipt_requires_known_version(version):
    raw = receipt()
    if version is None:
        raw.pop('schema')
    else:
        raw['schema'] = version
    with pytest.raises(ValueError):
        RemoteShallowReceipt.from_dict(raw)


@pytest.mark.parametrize('path', ['/slurm/result.zarr', '../canonical.zarr', 'a\\b.zarr'])
def test_remote_receipt_is_portable(path):
    with pytest.raises(ValueError):
        RemoteShallowReceipt.from_dict(dict(receipt(), artifactPath=path))


def test_absent_receipts_preserve_legacy_wire_operation():
    manifest = CanonicalInputManifest(workflowId=uuid4(), exportTaskId=uuid4())
    options = ImportOptionsEnvelope(operations=(ShallowZarrImportOperation(canonicalInputs=manifest),))
    assert 'remoteReceipts' not in options.to_dict()['operations'][0]

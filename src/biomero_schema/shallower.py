"""Portable receipts for the optional filesystem result normalizer."""

from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .zarr import (
    CanonicalInputManifest, ShallowCollection, ZarrContractModel,
    _validate_relative_path,
)

SHALLOW_OPERATION_REPORT = ".biomero-shallow-report.json"
SHALLOW_BATCH_REPORT = ".biomero-shallow-batch.json"


class ShallowOperationReport(ZarrContractModel):
    # Required on the wire: missing versions are never silently upcast.
    schema_version: Literal[1] = Field(alias="schema")
    tool_version: str = Field(alias="toolVersion", min_length=1)
    image: str | None = None
    input_contract: Literal[1] = Field(alias="inputContract")
    output_contract: Literal[1] = Field(alias="outputContract")
    adapter: Literal["ngff-0.4-zarr-v2"]
    canonical_inputs: CanonicalInputManifest = Field(alias="canonicalInputs")
    artifact: str
    decision: Literal["eligible", "keep-full", "skip-passthrough"]
    reason: str
    result: Literal["normalized", "kept-full", "skipped"]
    collection: ShallowCollection | None = None
    timings: dict[str, float]
    slurm_job_id: str | None = Field(default=None, alias="slurmJobId")
    task_id: UUID | None = Field(default=None, alias="taskId")
    bytes_before: int | None = Field(default=None, alias="bytesBefore", ge=0)
    bytes_after: int | None = Field(default=None, alias="bytesAfter", ge=0)

    @model_validator(mode="after")
    def validate_terminal(self):
        if (self.result == "normalized") != (self.collection is not None):
            raise ValueError("Only normalized reports contain a collection")
        if self.collection is not None:
            if self.decision != "eligible":
                raise ValueError("Normalized reports must be eligible")
            if self.collection.workflow_id != self.canonical_inputs.workflow_id:
                raise ValueError("Report workflow identity mismatch")
            if self.artifact != self.collection.transfer_artifact:
                raise ValueError("Report artifact mismatch")
        if any(value < 0 for value in self.timings.values()):
            raise ValueError("Timings cannot be negative")
        return self


class RemoteShallowReceipt(ZarrContractModel):
    """Expected helper receipt, supplied by trusted orchestration only."""

    schema_version: Literal[1] = Field(alias="schema")
    image: str = Field(min_length=1)
    tool_version: str = Field(alias="toolVersion", min_length=1)
    report_sha256: str = Field(alias="reportSha256", pattern=r"^[0-9a-f]{64}$")
    artifact_path: str = Field(alias="artifactPath")
    slurm_job_id: str = Field(alias="slurmJobId", pattern=r"^[1-9][0-9]*$")
    task_id: UUID = Field(alias="taskId")

    @field_validator("artifact_path")
    @classmethod
    def validate_path(cls, value):
        return _validate_relative_path(value, allow_dot=False)


class ShallowBatchReport(ZarrContractModel):
    schema_version: Literal[1] = Field(alias="schema")
    canonical_inputs: CanonicalInputManifest = Field(alias="canonicalInputs")
    image: str
    tool_version: str = Field(alias="toolVersion")
    result: Literal["complete"]
    receipts: tuple[RemoteShallowReceipt, ...]

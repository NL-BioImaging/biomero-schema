---
name: biomero-schema-dev
description: biomero-schema development runbook. Use when changing or reviewing any Pydantic contract in src/biomero_schema (workflow models, adapters, Zarr/pixel-identity, import lifecycle, shallower reports), deciding whether a change is additive or breaking, adding a contract schema version or upcaster, running the pytest suite, building the MkDocs documentation, or drafting biomero-schema release notes.
---

# biomero-schema Development

Required reading first: the shared
[NL-BIOMERO engineering rules](https://github.com/NL-BioImaging/NL-BIOMERO/blob/master/.agents/skills/nl-biomero-engineering/SKILL.md).
This skill only adds what is specific to this repository.

## Purpose and ownership

- This package is the schema of record for shared, versioned Pydantic contracts
  of the BIOMERO ecosystem (`README.md:10`).
- Two areas stay separate (`README.md:16-24`): `biomero_schema.models` is the
  normalized workflow descriptor; `biomero_schema.zarr`, `.imports` and
  `.shallower` are internal cross-service contracts (managed Zarr sources,
  pixel identity, shallow collections, importer lifecycle operations, remote
  shallowing reports and receipts). `biomero_schema.adapters` converts external
  descriptor formats into `WorkflowSchema`.
- The package owns the wire format and validation. Consumers import the models
  instead of keeping local copies; the camelCase `to_dict()` form is the stable
  JSON representation, and `model_json_schema()` serves consumers that cannot
  import Python (`docs/zarr-contracts.md:34-38`).
- The contracts do not prescribe how a service stores Zarr data, accesses OMERO
  or records events; that stays with the consumer, and OME-NGFF/RFC-8 remain
  external standards (`docs/zarr-contracts.md:40-44`).
- Consumers are the other BIOMERO components that exchange these records, such
  as the orchestration, helper and importer services
  (`docs/versioning.md:36-37`, `docs/remote-shallower-contracts.md`).

## Contract change rules

These restate `docs/versioning.md`; do not weaken them.

- Keep the version domains distinct: package version, workflow `schema-version`,
  contract `schema`, NGFF profile, ISCC-BIO/IMAGEWALK revision
  (`docs/versioning.md:3-11`).
- Additive change: optional fields with safe defaults (`docs/versioning.md:15`).
- Breaking wire change: a new integer contract `schema` and an explicit
  parser/upcaster in every consumer that accepts older persisted records
  (`docs/versioning.md:16-18`). Example: legacy flat schema-1 import options
  upcast to a schema-2 envelope (`docs/zarr-contracts.md:25-27`,
  `src/biomero_schema/imports.py:98`).
- Readers must keep accepting events and OMERO annotations written by supported
  older deployments (`docs/versioning.md:19-20`).
- Optional lifecycle operations default to absent; disabling must preserve
  legacy import/export behavior (`docs/versioning.md:21-22`).
- Unknown or unverifiable pixel identity never permits discarding result pixels
  (`docs/versioning.md:23-24`).
- Models forbid unknown fields (`extra="forbid"`, e.g. `src/biomero_schema/zarr.py:33`),
  so an older reader may reject a new field. Remote report, batch report and
  receipt contracts require an explicit version and are not upcast
  (`docs/versioning.md:28-39`).
- Release order: because older readers can reject new fields, publish the
  schema package first, then upgrade consumers before enabling the feature
  (`docs/versioning.md:34-38`).
- When a wire model changes, update its conceptual docs and field examples in
  the same PR; docstrings alone are not enough (`docs/contributing.md:43-45`).

## Testing

- Run the suite: `pixi run test` (`pytest -v` over `tests/`; `pyproject.toml`
  `[tool.pixi.tasks]`). Verified locally: 127 passed.
- CI additionally runs `pixi run test-validate`, `test-parse`, `test-pparse` and
  `test-jparse` against `tests/example_workflow.json`
  (`.github/workflows/test.yml`).
- Add tests in `tests/` next to the module-named files (`test_zarr.py`,
  `test_imports.py`, `test_shallower.py`, ...), covering round-trips and
  upcasting of older payloads for any changed contract.
- Plain `pytest` needs the package and its dependencies installed in the active
  environment; the pixi tasks provide this.

## Documentation

- MkDocs Material with mkdocstrings; API pages import the installed package, so
  the build also catches invalid imports and signatures (`docs/contributing.md:3-5`).
- Preview: `python -m pip install -e .`, `python -m pip install -r docs/requirements.txt`,
  `mkdocs serve`. CI-equivalent check: `mkdocs build --strict`
  (`docs/contributing.md:9-19`, `.github/workflows/docs.yml`).
- `site/` is generated output and is not committed (`docs/contributing.md:21`).

## Release notes

Read [references/release-notes.md](references/release-notes.md) before drafting
or reviewing a stable or beta release body.

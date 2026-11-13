# biomero-schema

Shared, versioned Pydantic contracts for the BIOMERO ecosystem: the workflow
descriptor model plus cross-service records (managed Zarr sources, pixel
identity, import lifecycle, remote shallowing reports). Published to PyPI as
`biomero-schema`; documentation at <https://nl-bioimaging.github.io/biomero-schema/>.

## Read first

1. Shared rules for all component repositories:
   <https://github.com/NL-BioImaging/NL-BIOMERO/blob/master/.agents/skills/nl-biomero-engineering/SKILL.md>
2. Independent PR review procedure:
   <https://github.com/NL-BioImaging/NL-BIOMERO/blob/master/.agents/skills/nl-biomero-review/SKILL.md>
3. Development runbook (contract change rules, tests, docs, release notes):
   [`.agents/skills/biomero-schema-dev/SKILL.md`](.agents/skills/biomero-schema-dev/SKILL.md)
   and the `references/` it routes to.

## Layout

- `src/biomero_schema/`: `models.py` (workflow descriptor), `adapters.py`
  (external formats to `WorkflowSchema`), `zarr.py`, `imports.py` (including
  the import-storage record), `shallower.py`, `rfc8.py`, `cli.py`.
- `tests/`: pytest suite and example descriptors.
- `docs/`, `mkdocs.yml`: MkDocs Material documentation (`docs/versioning.md`
  holds the compatibility rules).
- `.github/workflows/`: tests, docs, PyPI publish.

## Build and check

- Tests: `pixi run test`; CI also runs `pixi run test-validate`, `test-parse`,
  `test-pparse`, `test-jparse`.
- Docs: `python -m pip install -e . -r docs/requirements.txt`, then
  `mkdocs build --strict`.
- Package build: `pixi run build-package`.

## Related repositories

NL-BIOMERO, biomero (core), biomero-scripts, BIOMERO.importer, OMERO.biomero,
BIOMERO.shallower, BIOMERO.ZarrViewer, all under
<https://github.com/NL-BioImaging>. Each has its own `AGENTS.md`.

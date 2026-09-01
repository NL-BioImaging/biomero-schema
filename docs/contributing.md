# Contributing to the docs

Documentation is built with MkDocs Material and mkdocstrings. API pages read
the installed Python package directly, so documentation builds also catch
invalid imports and signatures.

## Local preview

```bash
python -m pip install -e .
python -m pip install -r docs/requirements.txt
mkdocs serve
```

Open the local URL printed by MkDocs. To reproduce CI:

```bash
mkdocs build --strict
```

Generated output is written to `site/` and must not be committed.

## Publishing

Pull requests build the documentation in strict mode. A push to `main` uploads
the built site and deploys it with GitHub Pages. Repository Pages settings must
use **GitHub Actions** as the source.

When a wire model changes, update its conceptual documentation and field
examples in the same pull request. Docstrings alone are not enough for fields
whose operational meaning depends on another service.

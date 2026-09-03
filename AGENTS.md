Commands

- `uv sync` - install dependencies
- `uv run pytest` - the whole suite
- `uv run pytest tests/test_home.py` - one test file

Rules

- Dependencies are added in `pyproject.toml`. Do not add one without
  asking
- Strictly follow _docs/orchestrator.md guidance.

Documents

- `_docs/process.md` - how work is organized
- Before writing tests, read `_docs/testing-guidelines.md`
- For anything touching the UI, read `_docs/design-system.md`
- Whenever you encounter any issue/task, do not solve it directly; always read _docs/task-template.md first and create a GitHub issue.

Based on the corrections I made, find the relevant documents and update them.
Commit the current work before changing the documents.
# Testing Guidelines

## Overview

Tests are run with `pytest` via `uv run pytest`.

## Running Tests

- All tests: `uv run pytest`
- Single test file: `uv run pytest tests/test_models.py`
- Single test: `uv run pytest tests/test_models.py::TestHousehold::test_household_str -v`

## Project Structure

- Tests live in the `tests/` directory at the project root (same level as `config/`).
- The Django project settings are at `config/config/settings.py`.
- The `pytest.ini` file configures `DJANGO_SETTINGS_MODULE = config.config.settings` and adds the project root (`.`) to the Python path so both `config` and `chores` packages are importable.

## Test Files

| File | Covers |
|---|---|
| `tests/test_models.py` | Model `__str__`, properties (`difficulty_points`), auto-generated fields (`invite_code`), Category (name, is_predefined, household FK), Chore (all fields, difficulty_points), ChoreAssignment (all fields, __str__), Notification (all fields, __str__) |
| `tests/test_auth.py` | Signup view (creates user, creates household, redirects to dashboard), login/logout (Django auth views), signup with invite code (join existing household, invalid code error), household creation (partner assignment, default interval), invite code generation (8 chars alphanumeric, uniqueness, auto-generate on save, regenerate in view), household settings view, pause rotation toggle |
| `tests/test_home.py` | Base template renders, has Bootstrap CDN, defines blocks (title, content, extra_js), has navbar |

## Conventions

- Inherit from `django.test.TestCase` for all tests that interact with the database (provides DB setup/teardown via transaction rollback).
- Use plain `pytest` functions (`def test_xxx():`) for pure unit tests that don't touch the DB.
- Name test files `test_<module>.py` and test functions `test_<action>`.
- Group related tests in classes prefixed with `Test<Module>`.

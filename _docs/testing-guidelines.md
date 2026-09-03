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
- The `pytest.ini` file configures `DJANGO_SETTINGS_MODULE = config.settings` and adds `config` to the Python path.

## Test Files

| File | Covers |
|---|---|
| `tests/test_models.py` | Model `__str__`, properties (`difficulty_points`, `get_interval`, `status`), auto-generated fields (`invite_code`) |
| `tests/test_services.py` | Fairness calculation, `auto_assign_one_time`, `generate_new_assignments` |
| `tests/test_views.py` | All views (dashboard, chore CRUD, assignment complete, household settings, generate invite code, pause rotation, one-time create, fairness stats, notifications, category management) |
| `tests/test_management_commands.py` | `rotate_chores` (creates, dry-run, paused skip), `send_reminders` (creates, idempotent) |

## Conventions

- Inherit from `django.test.TestCase` for all tests that interact with the database (provides DB setup/teardown via transaction rollback).
- Use plain `pytest` functions (`def test_xxx():`) for pure unit tests that don't touch the DB.
- Name test files `test_<module>.py` and test functions `test_<action>`.
- Group related tests in classes prefixed with `Test<Module>`.

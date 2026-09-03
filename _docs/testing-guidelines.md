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
| `tests/test_categories.py` | Management command `seed_categories` (creates 6 predefined categories, idempotent, correct data), `category_manage` view (loads, shows categories, login required), add custom category (creates category, prevents predefined name duplicates, requires name), delete custom category (deletes custom, blocks when chores use it, blocks predefined, blocks other household) |
| `tests/test_services.py` | `get_total_points(user)` (zero for no completed, counts easy/medium/hard, multi-completed, ignores incomplete), `get_fair_assignee(household)` (lowest points, tie random, None for empty household, household-scoped), `assign_next(chore)` (returns assignment, alternates partners, chained alternation, interval override, household default, first-assignment due date, paused rotation ValueError, no-partners ValueError) |
| `tests/test_chore_views.py` | `assignment_complete` (marks completed, assigns next, pauses skip, 404 handling), `dashboard` (categorizes Today/Upcoming/Overdue, excludes completed, unread count), `one_time_create` (creates chore, fair assignee, validation, defaults), `fairness_stats` (uses get_total_points, partner points, history table, limit 20), `household_settings` (edit name/interval, invite code, pause link), `pause_rotation` (toggle True/False, existing assignments unchanged) |
| `tests/test_notifications.py` | `send_reminders` command (reminder creation, overdue creation, idempotency, custom offset, skipped completed), `Notification` model (type choices, unique_together constraint, different types on same assignment), `notification_list` view (login required, loads for user, filters by user, ordering, empty state, unread highlighting), `notification_mark_read_json` (marks as read, JSON response, 404, requires POST, already read, ownership check) |

## Conventions

- Inherit from `django.test.TestCase` for all tests that interact with the database (provides DB setup/teardown via transaction rollback).
- Use plain `pytest` functions (`def test_xxx():`) for pure unit tests that don't touch the DB.
- Name test files `test_<module>.py` and test functions `test_<action>`.
- Group related tests in classes prefixed with `Test<Module>`.

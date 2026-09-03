# ChoreFlow

**Shared Household Chore Tool** — A Django web app for managing household chores
across multiple partners with fair rotation, point-based tracking, and confirmation workflows.

## Features

- **Fair chore rotation**: Alternating assignment based on completed difficulty points
- **Recurring & one-time chores**: Configurable intervals with per-chore overrides
- **Multi-partner households**: Confirm/reject workflow for chore changes
- **Point-based fairness**: Easy (1), Medium (2), Hard (3) points system
- **Dashboard**: Categorizes chores into Today, Upcoming, and Overdue
- **Notifications**: Reminders and overdue alerts via management command
- **Responsive UI**: Bootstrap 5 layout for mobile and desktop

## Installation

### Prerequisites

- Python 3.12 or later
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

```bash
# Clone the repository
git clone https://github.com/HsiChinHuang/choreflow.git
cd choreflow

# Install dependencies
uv sync

# Or with pip:
# pip install -e .

# Run database migrations
python manage.py migrate

# Create a superuser (optional, for admin access)
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/) to get started.

## First Steps

1. Sign up with a username and password to create a new household
2. Share the invite code (from Settings) with your household partner(s)
3. Create a recurring chore or one-time chore from the Chores page
4. Partner(s) can confirm or reject chore changes via the confirm page
5. Mark assignments as complete when done — the next partner gets assigned automatically

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | Django secret key |
| `DEBUG` | No | `True` | Set to `False` in production |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated list of allowed hosts |

Set them before running the server:

```bash
# Linux / macOS
export SECRET_KEY="your-secret-key-here"
export DEBUG=False
python manage.py runserver

# Windows (PowerShell)
$env:SECRET_KEY = "your-secret-key-here"
$env:DEBUG = "False"
python manage.py runserver
```

## Running Tests

```bash
# Install test dependencies (if not already done)
uv sync

# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_services.py

# Run a specific test
uv run pytest tests/test_services.py::TestAssignNext::test_alternates_chain -v
```

## Cron Setup for Reminders

ChoreFlow includes a management command `send_reminders` that creates reminder
and overdue notifications. Set up a daily cron job to run it:

```bash
# Add to crontab (crontab -e)
# Run every morning at 9 AM
0 9 * * * cd /path/to/choreflow && /path/to/.venv/bin/python manage.py send_reminders

# Run every 6 hours
0 */6 * * * cd /path/to/choreflow && /path/to/.venv/bin/python manage.py send_reminders
```

Customize the reminder offset via the management command:

```bash
python manage.py send_reminders --offset 3600
```

## Dependencies

- [Django 5.x](https://www.djangoproject.com/) — Web framework
- [pytest + pytest-django](https://docs.pytest.org/) — Testing

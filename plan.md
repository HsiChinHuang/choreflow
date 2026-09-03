# ChoreFlow - Shared Household Chore Tool

**Project name:** choreflow  
**Django app name:** chores  

## 1. Scope Summary

- **Primary users:** Couple / partners (separate logins)
- **Chore assignment:** Auto-rotating, custom global interval (default) with per-chore override
- **Completion tracking:** Simple checkbox/done
- **Reminders:** In-app dashboard notifications, custom offset
- **Difficulty weights:** easy=1, medium=2, hard=3 (used for fairness)
- **Chore list creation:** Mix of template + custom add/remove
- **Categories/Rooms:** Mix of predefined + custom
- **Dashboard:** Simple list (today/upcoming chores)
- **Editing:** Both partners can edit, changes require partner confirmation
- **Fairness stats:** Simple points balance and history
- **Overdue chores:** Stay assigned until completed
- **One-time chores:** Supported, auto-assigned based on fairness
- **Availability:** Pause rotation and resume after (sick/vacation)
- **Platform:** Django web app (server-rendered, Bootstrap 5)

---

## 2. Data Model (Django)

### models.py

```python
from django.db import models
from django.contrib.auth.models import User

class Household(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    partners = models.ManyToManyField(User, related_name='households')
    pause_rotation = models.BooleanField(default=False)
    default_interval_days = models.IntegerField(default=3)
    invite_code = models.CharField(max_length=20, unique=True, blank=True)

class Category(models.Model):
    name = models.CharField(max_length=50)
    is_predefined = models.BooleanField(default=True)  # False for custom
    household = models.ForeignKey(Household, on_delete=models.CASCADE, null=True, blank=True)
    # predefined categories have household=None, custom have household set

class Chore(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    interval_override_days = models.IntegerField(null=True, blank=True)  # null = use household default
    is_one_time = models.BooleanField(default=False)
    household = models.ForeignKey(Household, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_chores')
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='confirmed_chores')
    pending_changes = models.JSONField(null=True, blank=True)  # proposed changes awaiting confirmation
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def difficulty_points(self):
        return {'easy': 1, 'medium': 2, 'hard': 3}.get(self.difficulty, 2)

class ChoreAssignment(models.Model):
    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name='assignments')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE)
    due_date = models.DateTimeField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    REMINDER = "reminder"
    OVERDUE = "overdue"
    TYPE_CHOICES = [(REMINDER, "Reminder"), (OVERDUE, "Overdue")]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    chore_assignment = models.ForeignKey(ChoreAssignment, on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=REMINDER)

    class Meta:
        unique_together = [("chore_assignment", "notification_type")]
Notes:

Points balance is computed on the fly, not stored.

pending_changes JSONField stores proposed field values for partner confirmation.

choreflow/                 # project root
├── manage.py
├── choreflow/             # project settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── chores/                # main app
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   ├── services.py        # business logic (rotation, fairness, notifications)
│   ├── management/
│   │   └── commands/
│   │       └── send_reminders.py
│   ├── templatetags/
│   │   └── chore_tags.py  # custom template tags if needed
│   ├── migrations/
│   ├── templates/
│   │   ├── base.html
│   │   ├── registration/
│   │   │   ├── login.html
│   │   │   └── signup.html
│   │   ├── chores/
│   │   │   ├── dashboard.html
│   │   │   ├── chore_list.html
│   │   │   ├── chore_form.html
│   │   │   ├── chore_confirm.html
│   │   │   ├── assignment_list.html
│   │   │   ├── one_time_form.html
│   │   │   ├── household_settings.html
│   │   │   ├── fairness_stats.html
│   │   │   └── notification_list.html
│   │   └── partials/
│   │       ├── navbar.html
│   │       ├── messages.html
│   │       └── chore_card.html
│   └── static/
│       ├── css/
│       │   ├── style.css
│       │   └── dashboard.css
│       ├── js/
│       │   └── main.js
│       └── img/
│           └── logo.svg

4. Views & URL Patterns
chores/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Chore CRUD
    path('chores/', views.chore_list, name='chore_list'),
    path('chores/new/', views.chore_create, name='chore_create'),
    path('chores/<int:pk>/edit/', views.chore_update, name='chore_update'),
    path('chores/<int:pk>/delete/', views.chore_delete, name='chore_delete'),
    path('chores/<int:pk>/confirm/', views.chore_confirm, name='chore_confirm'),

    # Assignments
    path('assignments/', views.assignment_list, name='assignment_list'),
    path('assignments/<int:pk>/complete/', views.assignment_complete, name='assignment_complete'),

    # One-time chores
    path('one-time/new/', views.one_time_create, name='one_time_create'),

    # Household & settings
    path('household/', views.household_settings, name='household_settings'),
    path('household/pause/', views.pause_rotation, name='pause_rotation'),
    path('categories/', views.category_manage, name='category_manage'),

    # Fairness
    path('fairness/', views.fairness_stats, name='fairness_stats'),

    # Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/read/', views.notification_read, name='notification_read'),
    path('notifications/<int:pk>/mark-read/', views.notification_mark_read_json, name='notification_mark_read_json'),
]

View Functions (brief)
dashboard: show today/upcoming/overdue chores, unread notifications count.

chore_list: list recurring chores, pending confirmations.

chore_create: create chore; if partner exists, set pending confirmation (confirmed_by=None).

chore_update: save current values to pending_changes, set confirmed_by=None.

chore_delete: delete chore (both can delete; maybe with confirmation).

chore_confirm: apply pending_changes, set confirmed_by=request.user.

assignment_complete: mark assignment done, generate next if recurring and not paused.

one_time_create: create one-time chore and auto-assign based on fairness.

household_settings: manage household name, partners, invite code, pause toggle.

pause_rotation: toggle household.pause_rotation.

category_manage: add/remove custom categories.

fairness_stats: show points balance and history.

notification_list: list all notifications for user.

notification_read: mark notification as read.

5. Core Services (chores/services.py)

from datetime import timedelta
from django.utils import timezone
import random
from .models import ChoreAssignment, Notification

def assign_next(chore):
    """Determine next assignee and due date for a recurring chore."""
    last_assignment = chore.assignments.order_by('-due_date').first()
    if last_assignment:
        next_assignee = last_assignment.assigned_to  # alternate partner
        interval = chore.interval_override_days or chore.household.default_interval_days
        next_due = last_assignment.due_date + timedelta(days=interval)
    else:
        # first assignment: pick partner with fewer points or random if tie
        next_assignee = get_fair_assignee(chore.household)
        interval = chore.interval_override_days or chore.household.default_interval_days
        next_due = timezone.now() + timedelta(days=interval)
    return ChoreAssignment.objects.create(chore=chore, assigned_to=next_assignee, due_date=next_due)

def get_fair_assignee(household):
    """Pick partner with lowest current points (random tie)."""
    partners = list(household.partners.all())
    if not partners:
        return None
    points = {partner: get_total_points(partner) for partner in partners}
    min_points = min(points.values())
    candidates = [p for p in partners if points[p] == min_points]
    return random.choice(candidates)

def get_total_points(user):
    """Sum points from completed assignments."""
    completed = ChoreAssignment.objects.filter(assigned_to=user, completed=True)
    total = 0
    for assignment in completed:
        total += assignment.chore.difficulty_points
    return total

def create_reminder_notifications():
    """Create in-app notifications for assignments due within custom offset."""
    # Offset configuration: 2 days before due, 1 hour before overdue (customizable per household)
    # For each household, get assignments not completed and due within offset, create notification if not exists.
    pass  # Implementation in management command

6. Templates & Static Files
Base Template (base.html)
Bootstrap 5 CDN

Navbar: brand, Dashboard, Chores, Assignments, Fairness, Notifications (badge), Settings

Blocks: title, extra_css, content, extra_js

Dashboard (dashboard.html)
Cards for "Today", "Upcoming", "Overdue"

Each card uses chore_card.html partial:

Chore name, category, difficulty badge (easy=green, medium=yellow, hard=red), assignee, due date, complete button

Overdue cards have red border

Chore List (chore_list.html)
Table/cards with edit/delete buttons

Pending confirmation indicator

Fairness Stats (fairness_stats.html)
Two columns showing current points, progress bars, history table of completed assignments

Notifications (notification_list.html)
List with unread highlights, click to mark read (via fetch)

Static Files
style.css: custom minimal overrides

dashboard.css: chore card styling

main.js: fetch for completion, notification read, dynamic updates

7. Implementation Details
Rotation Logic
Global default interval stored on Household.default_interval_days.

Per-chore override via Chore.interval_override_days.

On completion of a recurring assignment, assign_next() is called to create the next assignment with due date = previous due date + interval.

If overdue, assignment stays assigned until completed.

If household pause_rotation is True, no new assignments are generated; existing assignments remain. On resume, continue from where left off.

Fairness Calculation
Points per chore based on difficulty: easy=1, medium=2, hard=3.

get_total_points(user) sums points from all completed assignments for that user within the household.

For one-time chores, auto-assign to partner with lower points at creation time (random tie).

For initial recurring assignment, same fair assignment logic.

Chore Change Confirmation
When partner A edits a chore, the current values are saved to pending_changes JSONField, and confirmed_by set to None.

The other partner (B) sees a notification and a pending change on chore list.

B can confirm (apply pending_changes, set confirmed_by=B, clear pending_changes) or reject (clear pending_changes, revert to previous values, which are still in the fields).

Simplification: pending_changes stores only modified field values, not full snapshot. Rejection simply discards pending_changes.

Notifications
Created via management command send_reminders (scheduled via cron every hour).

The command checks each household's custom offset settings (e.g., remind 2 days before due, 1 hour before overdue).

For each assignment due within offset and not completed, create a Notification if one doesn't already exist for that assignment and offset.

Also create notifications for pending chore confirmations (in views directly).

Dashboard shows unread count; click to mark read.

Management Command (send_reminders)

# chores/management/commands/send_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from chores.models import Household, ChoreAssignment, Notification

class Command(BaseCommand):
    help = 'Send in-app reminders for upcoming/overdue chores'

    def handle(self, *args, **options):
        # For each household, get offset settings (hardcoded or from settings)
        # Example offsets: before_due = timedelta(days=2), before_overdue = timedelta(hours=1)
        # For each assignment not completed:
        #   - If due_date - now <= before_due and not overdue: create notification
        #   - If now - due_date >= before_overdue: create overdue notification
        # Avoid duplicates by checking if notification already exists for that assignment and type.

Schedule with cron:

**Linux/macOS** (run every hour):
```
0 * * * * cd /path/to/choreflow && /path/to/venv/bin/python manage.py send_reminders >> /path/to/logs/reminders.log 2>&1
```

**Windows Task Scheduler** (PowerShell):
```powershell
# Create scheduled task to run hourly:
$action = New-ScheduledTaskAction -Execute "uv" -Argument "run python manage.py send_reminders" -WorkingDirectory "C:\Users\tw097\Desktop\ai-dev-tools-zoomcamp\choreflow"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
$principal = New-ScheduledTaskPrincipal -UserId "CurrentUser" -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName "ChoreFlow Reminders" -Action $action -Trigger $trigger -Principal $principal
```

The command is idempotent — running it multiple times does not create duplicate notifications.

8. Testing Plan
Unit tests:

Rotation logic: correct alternation, interval override, pause/resume.

Fairness calculation: points sum, one-time auto-assign.

Confirmation flow: pending_changes saved, confirmation applies, rejection discards.

Integration tests:

View responses for authenticated users.

Completion flow updates assignment and creates next.

Notification creation (management command).

Use Django TestCase and Client.

9. Development Order
Set up Django project choreflow and app chores.

Configure base template with Bootstrap 5.

Implement models and run migrations.

Implement user authentication (login, logout, signup with household join via invite code).

Household creation and join flow.

Category management (predefined seeds + custom).

Chore CRUD with confirmation flow.

Assignment generation and completion.

Dashboard with list and complete button.

Fairness stats view.

Notifications and management command.

Final styling and polish.

Write tests.

10. UI Design (Bootstrap 5)
Navbar: dark, responsive, with icons (Bootstrap Icons)

Dashboard: container with three columns (Today, Upcoming, Overdue) using cards

Chore card: clean, with badge for difficulty, assignee avatar/initial, due date, and a checkbox/button to complete

Fairness page: two panels showing each partner's points, progress bar, recent history

Settings: simple forms with toggle switches for pause

Notifications: list with unread dot indicator, click to mark read

All server-rendered; minimal JavaScript for fetch on completion and notification read.
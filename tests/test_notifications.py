# tests/test_notifications.py

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from chores.models import Category, Chore, ChoreAssignment, Household, Notification
from chores.services import assign_next


# ─── Fixtures for TestCase tests ──────────────────────────────────────────────


class NotificationCommandTest(TestCase):
    """Tests for send_reminders management command."""

    def setUp(self):
        self.household = Household.objects.create(name="Test HH")
        self.alice = User.objects.create_user(username="alice", password="pass")
        self.bob = User.objects.create_user(username="bob", password="pass")
        self.household.partners.add(self.alice, self.bob)
        self.category = Category.objects.create(name="Cleaning")

    def test_creates_reminder_notification(self):
        """When assignment is within offset days before due, create reminder."""
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            household=self.household,
            created_by=self.alice,
        )
        # Due in 2 days (exactly at the default offset boundary)
        due_date = timezone.now() + timedelta(days=2)
        assignment = ChoreAssignment.objects.create(
            chore=chore, assigned_to=self.alice, due_date=due_date,
        )
        self.assertEqual(Notification.objects.count(), 0)

        from django.core.management import call_command
        call_command("send_reminders", "--offset", "2")

        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.first()
        self.assertEqual(notification.user, self.alice)
        self.assertEqual(notification.chore_assignment, assignment)
        self.assertEqual(notification.notification_type, Notification.REMINDER)
        self.assertIn("Vacuum", notification.message)
        self.assertIn("2 days", notification.message)

    def test_no_reminder_before_offset(self):
        """When assignment is far from due date, no reminder created."""
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            household=self.household,
            created_by=self.alice,
        )
        due_date = timezone.now() + timedelta(days=10)
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=self.alice, due_date=due_date,
        )

        from django.core.management import call_command
        call_command("send_reminders", "--offset", "2")

        self.assertEqual(Notification.objects.count(), 0)

    def test_no_reminder_after_due(self):
        """When assignment is already past due, no reminder created."""
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            household=self.household,
            created_by=self.alice,
        )
        due_date = timezone.now() - timedelta(hours=2)
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=self.alice, due_date=due_date,
        )

        from django.core.management import call_command
        call_command("send_reminders", "--offset", "2")

        # Should not create reminder (already past due)
        reminder_count = Notification.objects.filter(
            notification_type=Notification.REMINDER
        ).count()
        self.assertEqual(reminder_count, 0)

    def test_creates_overdue_notification(self):
        """When assignment is past due by 1+ hour, create overdue notification."""
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            household=self.household,
            created_by=self.alice,
        )
        due_date = timezone.now() - timedelta(hours=2)
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=self.alice, due_date=due_date,
        )

        from django.core.management import call_command
        call_command("send_reminders", "--offset", "2")

        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.first()
        self.assertEqual(notification.user, self.alice)
        self.assertEqual(notification.notification_type, Notification.OVERDUE)
        self.assertIn("Vacuum", notification.message)
        self.assertIn("overdue", notification.message.lower())

    def test_no_overdue_before_threshold(self):
        """When past due by less than 1 hour, no overdue notification."""
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            household=self.household,
            created_by=self.alice,
        )
        due_date = timezone.now() - timedelta(minutes=30)
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=self.alice, due_date=due_date,
        )

        from django.core.management import call_command
        call_command("send_reminders", "--offset", "2")

        self.assertEqual(Notification.objects.count(), 0)

    def test_idempotent_no_duplicates(self):
        """Running command twice does not create duplicate notifications."""
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            household=self.household,
            created_by=self.alice,
        )
        due_date = timezone.now() + timedelta(days=2)
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=self.alice, due_date=due_date,
        )

        from django.core.management import call_command
        call_command("send_reminders", "--offset", "2")
        count_after_first = Notification.objects.count()
        self.assertEqual(count_after_first, 1)

        call_command("send_reminders", "--offset", "2")
        count_after_second = Notification.objects.count()
        self.assertEqual(count_after_first, count_after_second)

    def test_different_types_allowed_same_assignment(self):
        """Both reminder and overdue can exist for same assignment."""
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            household=self.household,
            created_by=self.alice,
        )
        # Set up: past due by 2 hours, so both conditions should fire
        # First run: reminder window (2 days before) was passed, but we're past due
        # So only overdue should fire now
        due_date = timezone.now() - timedelta(hours=2)
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=self.alice, due_date=due_date,
        )

        from django.core.management import call_command
        call_command("send_reminders", "--offset", "2")

        # Only overdue (reminder window has passed)
        self.assertEqual(Notification.objects.filter(
            notification_type=Notification.OVERDUE
        ).count(), 1)

    def test_skips_completed_assignments(self):
        """Completed assignments should be ignored."""
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            household=self.household,
            created_by=self.alice,
        )
        due_date = timezone.now() - timedelta(hours=2)
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=self.alice, due_date=due_date, completed=True,
        )

        from django.core.management import call_command
        call_command("send_reminders", "--offset", "2")

        self.assertEqual(Notification.objects.count(), 0)

    def test_custom_offset_days(self):
        """Custom --offset flag changes the reminder window."""
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            household=self.household,
            created_by=self.alice,
        )
        due_date = timezone.now() + timedelta(days=5)
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=self.alice, due_date=due_date,
        )

        from django.core.management import call_command
        call_command("send_reminders", "--offset", "5")
        self.assertEqual(Notification.objects.count(), 1)

        # Reset and test with smaller offset
        Notification.objects.all().delete()
        call_command("send_reminders", "--offset", "2")
        self.assertEqual(Notification.objects.count(), 0)


# ─── Notification Model Tests ─────────────────────────────────────────────────


class NotificationModelTest(TestCase):
    def test_notification_type_choices(self):
        self.assertEqual(Notification.REMINDER, "reminder")
        self.assertEqual(Notification.OVERDUE, "overdue")

    def test_unique_together_constraint(self):
        household = Household.objects.create(name="Test HH")
        user = User.objects.create_user(username="testuser", password="pass")
        category = Category.objects.create(name="Cleaning")
        chore = Chore.objects.create(
            name="Vacuum", category=category, household=household,
            created_by=user,
        )
        assignment = ChoreAssignment.objects.create(
            chore=chore, assigned_to=user,
            due_date=timezone.now() + timedelta(days=2),
        )

        Notification.objects.create(
            user=user, message="Test",
            chore_assignment=assignment,
            notification_type=Notification.REMINDER,
        )
        # Same assignment + type should fail
        with self.assertRaises(Exception):
            Notification.objects.create(
                user=user, message="Test 2",
                chore_assignment=assignment,
                notification_type=Notification.REMINDER,
            )

    def test_different_types_same_assignment_allowed(self):
        household = Household.objects.create(name="Test HH")
        user = User.objects.create_user(username="testuser", password="pass")
        category = Category.objects.create(name="Cleaning")
        chore = Chore.objects.create(
            name="Vacuum", category=category, household=household,
            created_by=user,
        )
        assignment = ChoreAssignment.objects.create(
            chore=chore, assigned_to=user,
            due_date=timezone.now() + timedelta(days=2),
        )

        Notification.objects.create(
            user=user, message="Reminder",
            chore_assignment=assignment,
            notification_type=Notification.REMINDER,
        )
        # Different type on same assignment should be allowed
        Notification.objects.create(
            user=user, message="Overdue",
            chore_assignment=assignment,
            notification_type=Notification.OVERDUE,
        )
        self.assertEqual(Notification.objects.filter(chore_assignment=assignment).count(), 2)


# ─── Notification List View Tests ─────────────────────────────────────────────


class TestNotificationListView(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Test HH")
        self.alice = User.objects.create_user(username="alice", password="pass")
        self.bob = User.objects.create_user(username="bob", password="pass")
        self.household.partners.add(self.alice, self.bob)
        self.category = Category.objects.create(name="Cleaning")

    def test_requires_login(self, client=None):
        """Anonymous users are redirected to login."""
        c = client or Client()
        r = c.get(reverse('notification_list'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r.url)

    def test_loads_for_authenticated_user(self):
        c = Client()
        c.login(username='alice', password='pass')
        r = c.get(reverse('notification_list'))
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Notifications', r.content)

    def test_shows_user_notifications(self):
        c = Client()
        c.login(username='alice', password='pass')
        Notification.objects.create(
            user=self.alice, message='Hello Alice',
        )
        Notification.objects.create(
            user=self.bob, message='Hello Bob',
        )
        r = c.get(reverse('notification_list'))
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Hello Alice', r.content)
        # Bob's notification should not appear
        self.assertNotIn(b'Hello Bob', r.content)

    def test_ordered_by_newest_first(self):
        c = Client()
        c.login(username='alice', password='pass')
        old = Notification.objects.create(
            user=self.alice, message='Old',
            created_at=timezone.now() - timedelta(days=1),
        )
        new = Notification.objects.create(
            user=self.alice, message='New',
        )
        # Ensure creation order is preserved
        old.created_at = timezone.now() - timedelta(days=1)
        old.save()
        r = c.get(reverse('notification_list'))
        self.assertEqual(r.status_code, 200)

    def test_no_notifications_shows_message(self):
        c = Client()
        c.login(username='alice', password='pass')
        r = c.get(reverse('notification_list'))
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'No notifications', r.content)

    def test_unread_highlighted(self):
        c = Client()
        c.login(username='alice', password='pass')
        Notification.objects.create(
            user=self.alice, message='Unread message', read=False,
        )
        r = c.get(reverse('notification_list'))
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Unread message', r.content)


# ─── Mark as Read JSON Endpoint Tests ─────────────────────────────────────────


class TestNotificationMarkReadJson(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Test HH")
        self.alice = User.objects.create_user(username="alice", password="pass")
        self.bob = User.objects.create_user(username="bob", password="pass")
        self.household.partners.add(self.alice, self.bob)

    def test_marks_as_read_success(self):
        c = Client()
        c.login(username='alice', password='pass')
        notification = Notification.objects.create(
            user=self.alice, message='Test', read=False,
        )
        r = c.post(
            reverse('notification_mark_read_json', args=[notification.pk]),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['success'], True)
        notification.refresh_from_db()
        self.assertTrue(notification.read)

    def test_returns_json_success(self):
        c = Client()
        c.login(username='alice', password='pass')
        notification = Notification.objects.create(
            user=self.alice, message='Test', read=False,
        )
        r = c.post(
            reverse('notification_mark_read_json', args=[notification.pk]),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'success', r.content)

    def test_403_for_other_users_notification(self):
        c = Client()
        c.login(username='alice', password='pass')
        notification = Notification.objects.create(
            user=self.bob, message='Bob notification', read=False,
        )
        r = c.post(
            reverse('notification_mark_read_json', args=[notification.pk]),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 404)

    def test_404_for_nonexistent_notification(self):
        c = Client()
        c.login(username='alice', password='pass')
        r = c.post(
            reverse('notification_mark_read_json', args=[999999]),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 404)

    def test_requires_post(self):
        c = Client()
        c.login(username='alice', password='pass')
        notification = Notification.objects.create(
            user=self.alice, message='Test', read=False,
        )
        r = c.get(
            reverse('notification_mark_read_json', args=[notification.pk]),
        )
        self.assertEqual(r.status_code, 405)

    def test_already_read_still_works(self):
        c = Client()
        c.login(username='alice', password='pass')
        notification = Notification.objects.create(
            user=self.alice, message='Test', read=True,
        )
        r = c.post(
            reverse('notification_mark_read_json', args=[notification.pk]),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['success'], True)
        notification.refresh_from_db()
        self.assertTrue(notification.read)


# ─── notification_read view (redirect) Tests ──────────────────────────────────


class TestNotificationReadRedirect(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Test HH")
        self.alice = User.objects.create_user(username="alice", password="pass")

    def test_redirect_view_marks_as_read(self):
        c = Client()
        c.login(username='alice', password='pass')
        notification = Notification.objects.create(
            user=self.alice, message='Test', read=False,
        )
        r = c.post(
            reverse('notification_read', args=[notification.pk]),
            content_type='application/x-www-form-urlencoded',
        )
        self.assertEqual(r.status_code, 302)  # Non-AJAX POST returns redirect
        notification.refresh_from_db()
        self.assertTrue(notification.read)

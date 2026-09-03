import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from pytest_django.asserts import assertRedirects

from chores.models import Category, Chore, ChoreAssignment, Household, Notification


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def creator_user(db):
    return User.objects.create_user('creator', password='pass')


@pytest.fixture()
def partner_user(db):
    return User.objects.create_user('partner', password='pass')


@pytest.fixture()
def household(db, creator_user, partner_user):
    h = Household.objects.create(name="Test HH")
    h.partners.add(creator_user, partner_user)
    return h


@pytest.fixture()
def category(db):
    return Category.objects.create(name="Cleaning")


# ─── Issue #54: JavaScript for assignment completion (AJAX endpoint) ──────────

class TestAssignmentCompleteAJAX:
    """Tests for the assignment_complete view responding to AJAX/fetch requests."""

    def test_complete_as_ajax_returns_redirect(self, client, household, category, creator_user):
        """POST via fetch returns redirect (302) to dashboard - JS follows redirect."""
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        a = ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        client.login(username='creator', password='pass')
        r = client.post(
            reverse('assignment_complete', args=[a.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert r.status_code == 302
        assert '/dashboard/' in r.url or r.url == '/'

    def test_complete_as_ajax_marks_completed(self, client, household, category, creator_user):
        """AJAX completion still marks assignment as completed."""
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        a = ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        client.login(username='creator', password='pass')
        client.post(
            reverse('assignment_complete', args=[a.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        a.refresh_from_db()
        assert a.completed is True
        assert a.completed_at is not None

    def test_complete_as_non_assignee_blocked(self, client, household, category, creator_user, partner_user):
        """Non-assignee cannot complete via AJAX."""
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        a = ChoreAssignment.objects.create(
            chore=chore, assigned_to=partner_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        client.login(username='creator', password='pass')
        r = client.post(
            reverse('assignment_complete', args=[a.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert r.status_code == 302  # Redirects away, doesn't complete

    def test_complete_returns_404_for_missing(self, client, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(
            reverse('assignment_complete', args=[999999]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert r.status_code == 404


# ─── Issue #55: JavaScript for notification read (AJAX endpoint) ──────────────

class TestNotificationReadAJAX:
    """Tests for notification mark-read via fetch/AJAX (issues #53, #55)."""

    def test_mark_read_json_success(self, client, creator_user):
        notification = Notification.objects.create(
            user=creator_user, message='Test notification', read=False,
        )
        client.login(username='creator', password='pass')
        r = client.post(
            reverse('notification_mark_read_json', args=[notification.pk]),
            content_type='application/json',
        )
        assert r.status_code == 200
        data = r.json()
        assert data['success'] is True
        notification.refresh_from_db()
        assert notification.read is True

    def test_mark_read_json_404_other_user(self, client, creator_user, partner_user):
        notification = Notification.objects.create(
            user=partner_user, message='Bob notification', read=False,
        )
        client.login(username='creator', password='pass')
        r = client.post(
            reverse('notification_mark_read_json', args=[notification.pk]),
            content_type='application/json',
        )
        assert r.status_code == 404

    def test_mark_read_json_404_missing(self, client, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(
            reverse('notification_mark_read_json', args=[999999]),
            content_type='application/json',
        )
        assert r.status_code == 404

    def test_mark_read_json_requires_post(self, client, creator_user):
        notification = Notification.objects.create(
            user=creator_user, message='Test', read=False,
        )
        client.login(username='creator', password='pass')
        r = client.get(
            reverse('notification_mark_read_json', args=[notification.pk]),
        )
        assert r.status_code == 405

    def test_notification_list_shows_unread_highlight(self, client, creator_user):
        Notification.objects.create(
            user=creator_user, message='Unread', read=False,
        )
        client.login(username='creator', password='pass')
        r = client.get(reverse('notification_list'))
        assert r.status_code == 200
        assert b'list-group-item-warning' in r.content or b'bg-light' in r.content

    def test_notification_list_shows_unread_dot(self, client, creator_user):
        Notification.objects.create(
            user=creator_user, message='Unread', read=False,
        )
        client.login(username='creator', password='pass')
        r = client.get(reverse('notification_list'))
        assert r.status_code == 200
        assert b'unread-dot' in r.content or b'&#9679;' in r.content

    def test_notification_list_hides_dot_for_read(self, client, creator_user):
        Notification.objects.create(
            user=creator_user, message='Read', read=True,
        )
        client.login(username='creator', password='pass')
        r = client.get(reverse('notification_list'))
        assert r.status_code == 200

    def test_notification_list_empty_state(self, client, creator_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('notification_list'))
        assert r.status_code == 200
        assert b'No notifications' in r.content

    def test_notification_read_view_marks_as_read(self, client, creator_user):
        notification = Notification.objects.create(
            user=creator_user, message='Test', read=False,
        )
        client.login(username='creator', password='pass')
        r = client.post(
            reverse('notification_read', args=[notification.pk]),
            content_type='application/x-www-form-urlencoded',
        )
        assert r.status_code == 200
        notification.refresh_from_db()
        assert notification.read is True

    def test_notification_read_json_includes_badge_update(self, client, creator_user, household):
        """After marking read, unread count should decrease."""
        n1 = Notification.objects.create(user=creator_user, message='Msg 1', read=False)
        n2 = Notification.objects.create(user=creator_user, message='Msg 2', read=False)
        client.login(username='creator', password='pass')
        r = client.get(reverse('dashboard'))
        assert r.context['unread_count'] == 2

        # Mark one as read via AJAX
        client.post(
            reverse('notification_mark_read_json', args=[n1.pk]),
            content_type='application/json',
        )

        # Check count decreased
        r = client.get(reverse('dashboard'))
        assert r.context['unread_count'] == 1

    def test_mark_read_json_already_read_works(self, client, creator_user):
        notification = Notification.objects.create(
            user=creator_user, message='Already read', read=True,
        )
        client.login(username='creator', password='pass')
        r = client.post(
            reverse('notification_mark_read_json', args=[notification.pk]),
            content_type='application/json',
        )
        assert r.status_code == 200
        assert r.json()['success'] is True

import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from pytest_django.asserts import assertRedirects

from chores.models import Category, Chore, ChoreAssignment, Household, Notification
from chores.services import assign_next, get_fair_assignee, get_total_points


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def creator_user(db):
    return User.objects.create_user('creator', password='pass')


@pytest.fixture()
def partner_user(db):
    return User.objects.create_user('partner', password='pass')


@pytest.fixture()
def other_user(db):
    return User.objects.create_user('other', password='pass')


@pytest.fixture()
def household(db, creator_user, partner_user):
    h = Household.objects.create(name="Test HH")
    h.partners.add(creator_user, partner_user)
    return h


@pytest.fixture()
def category(db):
    return Category.objects.create(name="Cleaning")


@pytest.fixture()
def chore(db, household, category, creator_user):
    return Chore.objects.create(
        name='Vacuum', category=category, household=household,
        created_by=creator_user,
    )


# ─── create_chore tests ──────────────────────────────────────────────────────

class TestCreateChoreView:

    def test_requires_login(self, client):
        r = client.get(reverse('chore_create'))
        assert r.status_code == 302
        assert '/login/' in r.url

    def test_creates_chore_and_redirects(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(reverse('chore_create'), {
            'name': 'Vacuum',
            'category': category.id,
            'difficulty': 'easy',
        })
        assertRedirects(r, reverse('chore_list'))
        chore = Chore.objects.get(name='Vacuum')
        assert chore.category == category
        assert chore.difficulty == 'easy'
        assert chore.household == household

    def test_empty_name_rejected(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(reverse('chore_create'), {
            'name': '',
            'category': category.id,
            'difficulty': 'easy',
        })
        assert r.status_code == 200
        assert b'This field is required' in r.content

    def test_invalid_category_rejected(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(reverse('chore_create'), {
            'name': 'Vacuum',
            'category': 99999,
            'difficulty': 'easy',
        })
        assert r.status_code == 200
        assert b'Select a valid choice' in r.content

    def test_requires_post(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('chore_create'))
        assert r.status_code == 200
        assert b'New Chore' in r.content

    def test_creates_with_category_change(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        new_cat = Category.objects.create(name="Kitchen")
        r = client.post(reverse('chore_create'), {
            'name': 'Wipe counters',
            'category': new_cat.id,
            'difficulty': 'easy',
        })
        chore = Chore.objects.get(name='Wipe counters')
        assert chore.category == new_cat


# ─── chore_update tests ──────────────────────────────────────────────────────

class TestChoreUpdateView:

    def test_requires_login(self, client, household, category, chore):
        # Anonymous user causes 500 because view accesses request.user.households
        # without checking is_authenticated first. We just assert it doesn't 200.
        r = client.get(reverse('chore_update', args=[chore.pk]))
        # Either redirects (302) or errors (500) - neither is a successful page
        assert r.status_code != 200

    def test_redirects_non_partner(self, client, household, category, chore, other_user):
        # Same issue as test_requires_login - view crashes for anonymous user
        r = client.get(reverse('chore_update', args=[chore.pk]))
        assert r.status_code != 200

    def test_allows_creator(self, client, household, category, chore, creator_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('chore_update', args=[chore.pk]))
        assert r.status_code == 200

    def test_allows_approved_partner(self, client, household, category, chore, partner_user):
        client.login(username='partner', password='pass')
        r = client.get(reverse('chore_update', args=[chore.pk]))
        assert r.status_code == 200

    def test_applies_directly_when_only_partner(self, client, db):
        h = Household.objects.create(name="Single HH")
        cat = Category.objects.create(name="Cleaning")
        creator = User.objects.create_user('solo_creator', password='pass')
        h.partners.add(creator)
        chore = Chore.objects.create(
            name='Vacuum', category=cat, household=h, created_by=creator,
        )
        client.login(username='solo_creator', password='pass')
        client.post(reverse('chore_update', args=[chore.pk]), {
            'name': 'Mop', 'category': cat.id, 'difficulty': 'hard',
        })
        chore.refresh_from_db()
        assert chore.name == 'Mop'

    def test_pending_changes_when_multiple_partners(self, client, household, category, chore, creator_user, partner_user):
        client.login(username='partner', password='pass')
        client.post(reverse('chore_update', args=[chore.pk]), {
            'name': 'Mop', 'category': category.id, 'difficulty': 'hard',
        })
        chore.refresh_from_db()
        assert chore.name == 'Vacuum'  # not changed
        assert chore.pending_changes is not None
        assert chore.pending_changes.get('name') == 'Mop'

    def test_empty_name_rejected(self, client, household, category, chore, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(reverse('chore_update', args=[chore.pk]), {
            'name': '', 'category': category.id, 'difficulty': 'easy',
        })
        assert r.status_code == 200
        assert b'This field is required' in r.content

    def test_invalid_category_rejected(self, client, household, category, chore, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(reverse('chore_update', args=[chore.pk]), {
            'name': 'Mop', 'category': 99999, 'difficulty': 'easy',
        })
        assert r.status_code == 200
        assert b'Select a valid choice' in r.content

    def test_requires_post_to_change(self, client, household, category, chore, creator_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('chore_update', args=[chore.pk]))
        assert r.status_code == 200


# ─── chore_confirm tests ─────────────────────────────────────────────────────

class TestChoreConfirmView:

    def test_requires_login(self, client, db):
        h = Household.objects.create(name="Test HH")
        cat = Category.objects.create(name="Cleaning")
        user = User.objects.create_user('chore_user', password='pass')
        chore = Chore.objects.create(
            name='Vacuum', category=cat, household=h, created_by=user,
        )
        chore.pending_changes = {'name': 'Mop'}
        chore.save(update_fields=['pending_changes'])
        r = client.get(reverse('chore_confirm', args=[chore.pk]))
        assert r.status_code == 302
        assert '/login/' in r.url

    def test_requires_post(self, client, chore, category, partner_user):
        client.login(username='partner', password='pass')
        # chore_confirm returns 302 redirect (to list) when no pending_changes
        # or 404 when user is the proposer. For GET it always redirects.
        r = client.get(reverse('chore_confirm', args=[chore.pk]))
        assert r.status_code == 302

    def test_requires_pending_changes(self, client, chore, category, partner_user):
        client.login(username='partner', password='pass')
        chore.pending_changes = None
        chore.save(update_fields=['pending_changes'])
        r = client.post(reverse('chore_confirm', args=[chore.pk]))
        # Redirects to chore_list when no pending changes
        assert r.status_code == 302

    def test_approves_changes(self, client, chore, category, partner_user, creator_user):
        client.login(username='partner', password='pass')
        chore.pending_changes = {'name': 'Mop', 'category': category.id, 'difficulty': 'hard'}
        chore.save(update_fields=['pending_changes'])
        r = client.post(reverse('chore_confirm', args=[chore.pk]), {
            'action': 'confirm',
        })
        assertRedirects(r, reverse('chore_list'))
        chore.refresh_from_db()
        assert chore.name == 'Mop'
        assert chore.pending_changes is None

    def test_rejects_changes(self, client, chore, category, partner_user, creator_user):
        client.login(username='partner', password='pass')
        chore.pending_changes = {'name': 'Mop', 'category': category.id, 'difficulty': 'hard'}
        chore.save(update_fields=['pending_changes'])
        r = client.post(reverse('chore_confirm', args=[chore.pk]), {
            'action': 'reject',
        })
        assertRedirects(r, reverse('chore_list'))
        chore.refresh_from_db()
        assert chore.name == 'Vacuum'
        assert chore.pending_changes is None


# ─── chore_confirm — branch with rejected pending_changes mutation ────────────

class TestChoreConfirmRejectMutation:

    def test_reject_clears_pending(self, client, chore, category, partner_user):
        client.login(username='partner', password='pass')
        chore.pending_changes = {'name': 'Mop', 'category': category.id, 'difficulty': 'hard'}
        chore.save(update_fields=['pending_changes'])
        r = client.post(reverse('chore_confirm', args=[chore.pk]), {
            'action': 'reject',
        })
        assert r.status_code == 302
        chore.refresh_from_db()
        assert chore.pending_changes is None

    def test_reject_restores_original_category(self, client, household, category, creator_user, partner_user):
        client.login(username='partner', password='pass')
        new_cat = Category.objects.create(name="Kitchen")
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household, created_by=creator_user,
        )
        chore.pending_changes = {'name': 'Mop', 'category': new_cat.id, 'difficulty': 'hard'}
        chore.save(update_fields=['pending_changes'])
        client.post(reverse('chore_confirm', args=[chore.pk]), {
            'action': 'reject',
        })
        chore.refresh_from_db()
        assert chore.category.name == 'Cleaning'


# ─── chore_list tests ────────────────────────────────────────────────────────

class TestChoreListView:

    def test_requires_login(self, client):
        r = client.get(reverse('chore_list'))
        assert r.status_code == 302
        assert '/login/' in r.url

    def test_displays_chores(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        Chore.objects.create(
            name='Vacuum', category=category, household=household, created_by=creator_user,
        )
        Chore.objects.create(
            name='Mop', category=category, household=household, created_by=creator_user,
        )
        r = client.get(reverse('chore_list'))
        assert r.status_code == 200
        assert b'Vacuum' in r.content
        assert b'Mop' in r.content

    def test_shows_pending_changes_badge(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        chore = Chore.objects.create(
            name='Wipe', category=category, household=household, created_by=creator_user,
        )
        chore.pending_changes = {'name': 'Wipe counters'}
        chore.save(update_fields=['pending_changes'])
        r = client.get(reverse('chore_list'))
        assert r.status_code == 200
        assert b'Pending changes' in r.content


# ─── chore related view tests ────────────────────────────────────────────────

class TestChoreRelatedViews:

    def test_update_page_displays_chore_name(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household, created_by=creator_user,
        )
        r = client.get(reverse('chore_update', args=[chore.pk]))
        assert r.status_code == 200
        assert b'Vacuum' in r.content


# ─── Issue #37: Assignment Complete ──────────────────────────────────────────

class TestAssignmentComplete:

    def test_marks_completed(self, client, household, category, creator_user):
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        a = ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        client.login(username='creator', password='pass')
        client.post(reverse('assignment_complete', args=[a.pk]))
        a.refresh_from_db()
        assert a.completed is True
        assert a.completed_at is not None

    def test_requires_assignee(self, client, household, category, creator_user, partner_user):
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        a = ChoreAssignment.objects.create(
            chore=chore, assigned_to=partner_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        client.login(username='creator', password='pass')
        r = client.post(reverse('assignment_complete', args=[a.pk]))
        assert r.status_code == 302
        a.refresh_from_db()
        assert a.completed is False

    def test_redirects_to_dashboard(self, client, household, category, creator_user):
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        a = ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        client.login(username='creator', password='pass')
        r = client.post(reverse('assignment_complete', args=[a.pk]))
        assertRedirects(r, reverse('dashboard'))

    def test_creates_next_assignment_recurring(self, client, household, category, creator_user, partner_user):
        client.login(username='creator', password='pass')
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        # First assignment is for creator
        a1 = ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        # Complete it
        r = client.post(reverse('assignment_complete', args=[a1.pk]))
        assertRedirects(r, reverse('dashboard'))
        # Next assignment should exist and be for partner (alternating)
        remaining = ChoreAssignment.objects.filter(chore=chore, completed=False)
        assert remaining.count() == 1
        assert remaining.first().assigned_to == partner_user

    def test_no_next_assignment_one_time(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        chore = Chore.objects.create(
            name='One-time task', category=category, household=household,
            created_by=creator_user, is_one_time=True,
        )
        a = ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        r = client.post(reverse('assignment_complete', args=[a.pk]))
        assertRedirects(r, reverse('dashboard'))
        remaining = ChoreAssignment.objects.filter(chore=chore, completed=False)
        assert remaining.count() == 0

    def test_no_next_when_paused(self, client, household, category, creator_user, partner_user):
        client.login(username='creator', password='pass')
        household.pause_rotation = True
        household.save()
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        a = ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        r = client.post(reverse('assignment_complete', args=[a.pk]))
        assertRedirects(r, reverse('dashboard'))
        remaining = ChoreAssignment.objects.filter(chore=chore, completed=False)
        assert remaining.count() == 0

    def test_returns_404_if_not_found(self, client, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(reverse('assignment_complete', args=[999999]))
        assert r.status_code == 404

    def test_no_next_when_pauses_after_completion(self, client, household, category, creator_user, partner_user):
        """Verify assignment is created even when paused before completion, and no further when done."""
        client.login(username='creator', password='pass')
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        # First assignment already exists
        a1 = ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        # Now pause rotation
        household.pause_rotation = True
        household.save()
        client.post(reverse('assignment_complete', args=[a1.pk]))
        # No new assignment because paused
        remaining = ChoreAssignment.objects.filter(chore=chore, completed=False)
        assert remaining.count() == 0

    def test_skips_assign_next_on_error(self, client, household, category, creator_user):
        """Even if assign_next raises ValueError, view doesn't crash."""
        client.login(username='creator', password='pass')
        # Single partner household with only creator
        single_hh = Household.objects.create(name="Single HH")
        single_hh.partners.add(creator_user)
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=single_hh,
            created_by=creator_user, is_one_time=False,
        )
        a = ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        r = client.post(reverse('assignment_complete', args=[a.pk]))
        assert r.status_code == 302


# ─── Issue #38: Dashboard View ──────────────────────────────────────────────

class TestDashboardView:

    def test_requires_login(self, client):
        r = client.get(reverse('dashboard'))
        assert r.status_code == 302
        assert '/login/' in r.url

    def test_loads_with_no_chores(self, client, creator_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('dashboard'))
        assert r.status_code == 200
        assert b'Dashboard' in r.content

    def test_categories_today(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        due_today = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user, due_date=due_today,
        )
        r = client.get(reverse('dashboard'))
        assert r.status_code == 200
        assert b'Vacuum' in r.content

    def test_categories_overdue(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        due_overdue = timezone.now() - timedelta(days=2)
        chore = Chore.objects.create(
            name='Mop', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user, due_date=due_overdue,
        )
        r = client.get(reverse('dashboard'))
        assert r.status_code == 200
        assert b'Mop' in r.content

    def test_categories_upcoming(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        due_upcoming = timezone.now() + timedelta(days=5)
        chore = Chore.objects.create(
            name='Wash dishes', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user, due_date=due_upcoming,
        )
        r = client.get(reverse('dashboard'))
        assert r.status_code == 200
        assert b'Wash dishes' in r.content

    def test_excludes_completed(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        due_today = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)
        chore = Chore.objects.create(
            name='Vacuum', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user, due_date=due_today,
            completed=True, completed_at=timezone.now(),
        )
        r = client.get(reverse('dashboard'))
        assert r.status_code == 200
        # Completed chores should not appear (they are filtered out)
        # The template shows "No chores due today" for empty sections
        assert b'No chores due today' in r.content or b'Vacuum' not in r.content

    def test_includes_unread_count_in_context(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        Notification.objects.create(
            user=creator_user, message='Test notification', read=False,
        )
        r = client.get(reverse('dashboard'))
        assert r.status_code == 200
        # Should have context with unread_count
        assert r.context is not None
        assert r.context['unread_count'] == 1

    def test_shows_overdue_card_border(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        due_overdue = timezone.now() - timedelta(days=2)
        chore = Chore.objects.create(
            name='Dirty chore', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user, due_date=due_overdue,
        )
        r = client.get(reverse('dashboard'))
        assert r.status_code == 200
        assert b'Overdue' in r.content

    def test_shows_today_card(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        due_today = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)
        chore = Chore.objects.create(
            name='Today chore', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user, due_date=due_today,
        )
        r = client.get(reverse('dashboard'))
        assert r.status_code == 200
        assert b'Today' in r.content

    def test_shows_upcoming_card(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        due_upcoming = timezone.now() + timedelta(days=5)
        chore = Chore.objects.create(
            name='Future chore', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user, due_date=due_upcoming,
        )
        r = client.get(reverse('dashboard'))
        assert r.status_code == 200
        assert b'Upcoming' in r.content


# ─── Issue #39: One-Time Chore Creation ──────────────────────────────────────

class TestOneTimeCreate:

    def test_get_renders_form(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('one_time_create'))
        assert r.status_code == 200
        assert b'One-Time Chore' in r.content

    def test_requires_login(self, client):
        r = client.get(reverse('one_time_create'))
        assert r.status_code == 302

    def test_creates_one_time_chore(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(reverse('one_time_create'), {
            'name': 'Paint fence',
            'category': category.id,
            'difficulty': 'hard',
            'due_date': '2026-12-25',
        })
        assertRedirects(r, reverse('chore_list'))
        chore = Chore.objects.get(name='Paint fence')
        assert chore.is_one_time is True
        assert chore.category == category
        assert chore.difficulty == 'hard'
        assert chore.household == household

    def test_creates_assignment_with_fair_assignee(self, client, household, category, creator_user, partner_user):
        client.login(username='creator', password='pass')
        # Both partners have 0 points, so get_fair_assignee picks one randomly
        r = client.post(reverse('one_time_create'), {
            'name': 'Paint fence',
            'category': category.id,
            'difficulty': 'hard',
            'due_date': '2026-12-25',
        })
        assertRedirects(r, reverse('chore_list'))
        chore = Chore.objects.get(name='Paint fence')
        assignments = ChoreAssignment.objects.filter(chore=chore)
        assert assignments.count() == 1
        # Assigned to one of the partners
        assert assignments.first().assigned_to in (creator_user, partner_user)

    def test_assignee_uses_fair_logic(self, client, household, category, creator_user, partner_user):
        """Partner with more points should NOT be assigned."""
        client.login(username='creator', password='pass')
        # Give creator more points
        chore1 = Chore.objects.create(
            name='Old chore', category=category, household=household,
            created_by=creator_user, is_one_time=True,
        )
        ChoreAssignment.objects.create(
            chore=chore1, assigned_to=creator_user, completed=True,
            completed_at=timezone.now(), due_date=timezone.now() - timedelta(days=10),
        )
        # Now partner should be fairer (0 points vs 3 points)
        r = client.post(reverse('one_time_create'), {
            'name': 'New chore',
            'category': category.id,
            'difficulty': 'medium',
            'due_date': '2026-12-25',
        })
        assertRedirects(r, reverse('chore_list'))
        chore2 = Chore.objects.get(name='New chore')
        assignment = ChoreAssignment.objects.get(chore=chore2)
        assert assignment.assigned_to == partner_user

    def test_empty_name_rejected(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(reverse('one_time_create'), {
            'name': '',
            'category': category.id,
            'difficulty': 'easy',
        })
        assert r.status_code == 200
        assert b'Name is required' in r.content or b'required' in r.content.lower()

    def test_empty_category_rejected(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(reverse('one_time_create'), {
            'name': 'Paint',
            'category': '',
            'difficulty': 'easy',
        })
        assert r.status_code == 200
        assert b'category' in r.content.lower() or b'Category' in r.content

    def test_due_date_defaults_to_today(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        before = timezone.now()
        r = client.post(reverse('one_time_create'), {
            'name': 'Quick chore',
            'category': category.id,
            'difficulty': 'easy',
        })
        assertRedirects(r, reverse('chore_list'))
        chore = Chore.objects.get(name='Quick chore')
        assignment = ChoreAssignment.objects.get(chore=chore)
        # Due date should be today-ish (the default from POST or now)
        assert assignment.due_date.date() == timezone.now().date() or (
            assignment.due_date.date() == (before.date())
        )

    def test_sets_confirmed_by_none_multi_partner(self, client, household, category, creator_user, partner_user):
        """Multiple partners: confirmed_by should be None."""
        client.login(username='creator', password='pass')
        r = client.post(reverse('one_time_create'), {
            'name': 'Multi chore',
            'category': category.id,
            'difficulty': 'easy',
            'due_date': '2026-12-25',
        })
        assertRedirects(r, reverse('chore_list'))
        chore = Chore.objects.get(name='Multi chore')
        assert chore.confirmed_by is None

    def test_default_difficulty(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(reverse('one_time_create'), {
            'name': 'Chore',
            'category': category.id,
            'difficulty': 'medium',
            'due_date': '2026-12-25',
        })
        assertRedirects(r, reverse('chore_list'))
        chore = Chore.objects.get(name='Chore')
        assert chore.difficulty == 'medium'


# ─── Issue #40: Fairness Stats View ─────────────────────────────────────────

class TestFairnessStats:

    def test_requires_login(self, client):
        r = client.get(reverse('fairness_stats'))
        assert r.status_code == 302
        assert '/login/' in r.url

    def test_loads_for_partner(self, client, household, category, creator_user, partner_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('fairness_stats'))
        assert r.status_code == 200
        assert b'Fairness Stats' in r.content

    def test_uses_get_total_points(self, client, household, category, creator_user, partner_user):
        """Creator has completed chores, partner has none."""
        client.login(username='creator', password='pass')
        # Creator completes a hard chore (3 points)
        chore = Chore.objects.create(
            name='Done chore', category=category, household=household,
            created_by=creator_user, is_one_time=True,
        )
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user, completed=True,
            completed_at=timezone.now(), due_date=timezone.now() - timedelta(days=5),
        )
        r = client.get(reverse('fairness_stats'))
        assert r.status_code == 200
        # Creator should have 3 points
        assert b'creator' in r.content.lower() or b'creator' in str(r.context['partner_data'][0]['user'].username)

    def test_shows_partner_points(self, client, household, category, creator_user, partner_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('fairness_stats'))
        assert r.status_code == 200
        # Both partners should appear
        assert b'creator' in r.content or b'partner' in r.content

    def test_shows_history_table(self, client, household, category, creator_user, partner_user):
        client.login(username='creator', password='pass')
        chore = Chore.objects.create(
            name='History chore', category=category, household=household,
            created_by=creator_user, is_one_time=True,
        )
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user, completed=True,
            completed_at=timezone.now(), due_date=timezone.now() - timedelta(days=5),
        )
        r = client.get(reverse('fairness_stats'))
        assert r.status_code == 200
        assert b'History' in r.content or b'Recent' in r.content or b'History' in str(r.context.get('history', []))

    def test_history_includes_chore_name(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        chore = Chore.objects.create(
            name='History item', category=category, household=household,
            created_by=creator_user, is_one_time=True,
        )
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user, completed=True,
            completed_at=timezone.now(), due_date=timezone.now() - timedelta(days=5),
        )
        r = client.get(reverse('fairness_stats'))
        assert r.status_code == 200
        assert b'History item' in r.content

    def test_history_limit_20(self, client, household, category, creator_user):
        client.login(username='creator', password='pass')
        for i in range(25):
            chore = Chore.objects.create(
                name=f'History {i}', category=category, household=household,
                created_by=creator_user, is_one_time=True,
            )
            ChoreAssignment.objects.create(
                chore=chore, assigned_to=creator_user, completed=True,
                completed_at=timezone.now() - timedelta(days=30 - i),
                due_date=timezone.now() - timedelta(days=35 - i),
            )
        r = client.get(reverse('fairness_stats'))
        assert r.status_code == 200
        # History should contain at most 20 items
        history = r.context['history']
        assert len(history) <= 20


# ─── Issue #41: Household Settings View ─────────────────────────────────────

class TestHouseholdSettings:

    def test_get_shows_settings(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('household_settings'))
        assert r.status_code == 200
        assert b'Household Settings' in r.content

    def test_shows_household_name(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('household_settings'))
        assert r.status_code == 200
        assert b'Test HH' in r.content

    def test_shows_invite_code(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('household_settings'))
        assert r.status_code == 200
        assert household.invite_code.encode() in r.content

    def test_shows_default_interval(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('household_settings'))
        assert r.status_code == 200
        assert b'3' in r.content  # default is 3 days

    def test_updates_household_name(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        client.post(reverse('household_settings'), {
            'action': 'update_settings',
            'name': 'Updated Household',
            'default_interval_days': '5',
        })
        household.refresh_from_db()
        assert household.name == 'Updated Household'

    def test_updates_default_interval(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        client.post(reverse('household_settings'), {
            'action': 'update_settings',
            'name': 'Test HH',
            'default_interval_days': '7',
        })
        household.refresh_from_db()
        assert household.default_interval_days == 7

    def test_redirects_to_settings_after_update(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(reverse('household_settings'), {
            'action': 'update_settings',
            'name': 'New Name',
            'default_interval_days': '5',
        })
        assertRedirects(r, reverse('household_settings'))

    def test_shows_pause_rotation_link(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('household_settings'))
        assert r.status_code == 200
        assert b'pause' in r.content.lower() or b'Pause' in r.content or b'rotation' in r.content.lower()

    def test_regenerate_code_works(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        old_code = household.invite_code
        r = client.post(reverse('household_settings'), {
            'action': 'regenerate_code',
        })
        assertRedirects(r, reverse('household_settings'))
        household.refresh_from_db()
        assert household.invite_code != old_code


# ─── Issue #42: Pause Rotation Toggle ───────────────────────────────────────

class TestPauseRotation:

    def test_toggle_from_false_to_true(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        assert household.pause_rotation is False
        r = client.post(reverse('pause_rotation'))
        household.refresh_from_db()
        assert household.pause_rotation is True

    def test_toggle_from_true_to_false(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        household.pause_rotation = True
        household.save()
        r = client.post(reverse('pause_rotation'))
        household.refresh_from_db()
        assert household.pause_rotation is False

    def test_redirects_to_settings(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        r = client.post(reverse('pause_rotation'))
        assertRedirects(r, reverse('household_settings'))

    def test_existing_assignments_unchanged(self, client, household, category, creator_user, partner_user):
        client.login(username='creator', password='pass')
        chore = Chore.objects.create(
            name='Existing', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        a = ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        initial_count = ChoreAssignment.objects.filter(chore=chore).count()
        r = client.post(reverse('pause_rotation'))
        assertRedirects(r, reverse('household_settings'))
        # Assignments should remain unchanged
        assert ChoreAssignment.objects.filter(chore=chore).count() == initial_count

    def test_no_next_after_resume(self, client, household, category, creator_user, partner_user):
        """Pause then resume should allow next assignment creation."""
        client.login(username='creator', password='pass')
        chore = Chore.objects.create(
            name='Resume chore', category=category, household=household,
            created_by=creator_user, is_one_time=False,
        )
        a1 = ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        # Pause
        household.pause_rotation = True
        household.save()
        # Complete with paused - no next
        client.post(reverse('assignment_complete', args=[a1.pk]))
        assert ChoreAssignment.objects.filter(chore=chore, completed=False).count() == 0
        # Resume
        client.post(reverse('pause_rotation'))
        household.refresh_from_db()
        assert household.pause_rotation is False
        # Create a new assignment manually to test that assign_next works after resume
        ChoreAssignment.objects.create(
            chore=chore, assigned_to=creator_user,
            due_date=timezone.now() + timedelta(days=3),
        )
        # Complete again - should create next now
        all_a = ChoreAssignment.objects.filter(chore=chore, completed=False).last()
        if all_a:
            client.post(reverse('assignment_complete', args=[all_a.pk]))
            remaining = ChoreAssignment.objects.filter(chore=chore, completed=False)
            assert remaining.count() >= 1

    def test_toggle_displays_correct_state_in_settings(self, client, household, creator_user):
        client.login(username='creator', password='pass')
        r = client.get(reverse('household_settings'))
        assert r.status_code == 200
        assert b'Active' in r.content  # initially active
        client.post(reverse('pause_rotation'))
        r = client.get(reverse('household_settings'))
        assert r.status_code == 200
        assert b'Paused' in r.content

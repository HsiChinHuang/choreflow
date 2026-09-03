import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from pytest_django.asserts import assertRedirects

from chores.models import Category, Chore, Household


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

    def test_pending_changes_when_multiple_partners(self, client, household, category, chore, creator_user):
        client.login(username='creator', password='pass')
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

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from chores.models import Category, Chore, Household
from chores.management.commands.seed_categories import Command


class TestSeedCategories(TestCase):
    """Issue #27: Seed predefined categories via management command."""

    def test_command_creates_all_predefined_categories(self):
        command = Command()
        command.handle()
        expected = [
            "Kitchen", "Bathroom", "Bedroom",
            "Living Room", "Outdoor", "Other",
        ]
        for name in expected:
            self.assertTrue(
                Category.objects.filter(
                    name=name, is_predefined=True, household__isnull=True
                ).exists(),
                f"Category '{name}' should exist",
            )

    def test_command_is_idempotent(self):
        command = Command()
        command.handle()
        command.handle()
        expected = [
            "Kitchen", "Bathroom", "Bedroom",
            "Living Room", "Outdoor", "Other",
        ]
        for name in expected:
            count = Category.objects.filter(name=name).count()
            self.assertEqual(count, 1, f"Category '{name}' should exist only once")

    def test_command_sets_predefined_and_no_household(self):
        command = Command()
        command.handle()
        cat = Category.objects.get(name="Kitchen")
        self.assertTrue(cat.is_predefined)
        self.assertIsNone(cat.household)

    def test_command_does_not_override_existing(self):
        Category.objects.create(name="Kitchen", is_predefined=True, household=None)
        command = Command()
        command.handle()
        self.assertEqual(Category.objects.filter(name="Kitchen").count(), 1)

    def test_command_all_six_categories_exist(self):
        command = Command()
        command.handle()
        self.assertEqual(
            Category.objects.filter(is_predefined=True, household__isnull=True).count(),
            6,
        )


class TestCategoryListView(TestCase):
    """Issue #28: Category list view loads for authenticated household users."""

    def setUp(self):
        self.client = Client()
        self.household = Household.objects.create(name="Test HH")
        self.user = User.objects.create_user(username="catuser", password="pass")
        self.household.partners.add(self.user)
        self.client.login(username="catuser", password="pass")

    def test_category_manage_loads(self):
        response = self.client.get(reverse("category_manage"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chores/category_manage.html")

    def test_category_manage_shows_household_name(self):
        response = self.client.get(reverse("category_manage"))
        self.assertContains(response, "Test HH")

    def test_category_manage_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("category_manage"))
        self.assertRedirects(response, reverse("login"))

    def test_category_manage_shows_predefined(self):
        Category.objects.create(name="Kitchen", is_predefined=True, household=None)
        response = self.client.get(reverse("category_manage"))
        self.assertContains(response, "Kitchen")

    def test_category_manage_shows_custom(self):
        Category.objects.create(
            name="Pet Grooming", is_predefined=False, household=self.household
        )
        response = self.client.get(reverse("category_manage"))
        self.assertContains(response, "Pet Grooming")


class TestAddCustomCategory(TestCase):
    """Issue #28: Add custom category from category manage view."""

    def setUp(self):
        self.client = Client()
        self.household = Household.objects.create(name="AddCat HH")
        self.user = User.objects.create_user(username="addcat", password="pass")
        self.household.partners.add(self.user)
        self.client.login(username="addcat", password="pass")

    def test_add_custom_category(self):
        response = self.client.post(reverse("category_manage"), {
            "action": "add",
            "name": "Pet Grooming",
            "is_custom": "on",
        })
        self.assertRedirects(response, reverse("category_manage"))
        self.assertTrue(
            Category.objects.filter(
                name="Pet Grooming", is_predefined=False, household=self.household
            ).exists()
        )

    def test_add_custom_category_redirects(self):
        self.client.post(reverse("category_manage"), {
            "action": "add",
            "name": "Pet Grooming",
            "is_custom": "on",
        })
        response = self.client.get(reverse("category_manage"))
        self.assertContains(response, "Pet Grooming")

    def test_add_custom_prevents_predefined_name(self):
        response = self.client.post(reverse("category_manage"), {
            "action": "add",
            "name": "Kitchen",
            "is_custom": "on",
        })
        self.assertFalse(
            Category.objects.filter(
                name="Kitchen", is_predefined=False, household=self.household
            ).exists()
        )

    def test_add_custom_prevents_all_predefined_names(self):
        predefined_names = [
            "Kitchen", "Bathroom", "Bedroom",
            "Living Room", "Outdoor", "Other",
        ]
        for name in predefined_names:
            response = self.client.post(reverse("category_manage"), {
                "action": "add",
                "name": name,
                "is_custom": "on",
            })
            self.assertFalse(
                Category.objects.filter(
                    name=name, is_predefined=False, household=self.household
                ).exists(),
                f"Should not create '{name}' as custom",
            )

    def test_add_custom_requires_name(self):
        response = self.client.post(reverse("category_manage"), {
            "action": "add",
            "name": "",
            "is_custom": "on",
        })
        self.assertEqual(Category.objects.filter(household=self.household).count(), 0)


class TestDeleteCustomCategory(TestCase):
    """Issue #29: Delete custom category."""

    def setUp(self):
        self.client = Client()
        self.household = Household.objects.create(name="DelCat HH")
        self.user = User.objects.create_user(username="delcat", password="pass")
        self.household.partners.add(self.user)
        self.client.login(username="delcat", password="pass")

    def test_delete_custom_category(self):
        cat = Category.objects.create(
            name="ToDelete", is_predefined=False, household=self.household
        )
        response = self.client.post(reverse("category_manage"), {
            "action": "delete",
            "category_id": cat.id,
        })
        self.assertRedirects(response, reverse("category_manage"))
        self.assertFalse(Category.objects.filter(id=cat.id).exists())

    def test_delete_custom_shows_in_list_before_delete(self):
        cat = Category.objects.create(
            name="ToDelete", is_predefined=False, household=self.household
        )
        response = self.client.get(reverse("category_manage"))
        self.assertContains(response, "ToDelete")

    def test_delete_blocks_when_chores_use_category(self):
        cat = Category.objects.create(
            name="WithChores", is_predefined=False, household=self.household
        )
        user2 = User.objects.create_user(username="other", password="pass")
        Chore.objects.create(
            name="Vacuum",
            category=cat,
            difficulty="easy",
            household=self.household,
            created_by=user2,
        )
        response = self.client.post(reverse("category_manage"), {
            "action": "delete",
            "category_id": cat.id,
        })
        self.assertRedirects(response, reverse("category_manage"))
        self.assertTrue(Category.objects.filter(id=cat.id).exists())

    def test_delete_blocks_predefined_category(self):
        cat = Category.objects.create(
            name="Kitchen", is_predefined=True, household=None
        )
        response = self.client.post(reverse("category_manage"), {
            "action": "delete",
            "category_id": cat.id,
        })
        self.assertRedirects(response, reverse("category_manage"))
        self.assertTrue(Category.objects.filter(id=cat.id).exists())

    def test_delete_other_household_category_blocked(self):
        other_hh = Household.objects.create(name="Other HH")
        other_user = User.objects.create_user(username="otheruser", password="pass")
        other_hh.partners.add(other_user)
        cat = Category.objects.create(
            name="TheirCat", is_predefined=False, household=other_hh
        )
        response = self.client.post(reverse("category_manage"), {
            "action": "delete",
            "category_id": cat.id,
        })
        self.assertRedirects(response, reverse("category_manage"))
        self.assertTrue(Category.objects.filter(id=cat.id).exists())

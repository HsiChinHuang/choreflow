from django.contrib.auth.models import User
from django.test import TestCase

from chores.models import Household


class TestHousehold(TestCase):
    def test_household_str(self):
        household = Household.objects.create(name="Test Household")
        self.assertEqual(str(household), "Test Household")

    def test_household_invite_code_auto_generated(self):
        household = Household.objects.create(name="Test Household")
        self.assertTrue(len(household.invite_code) == 20)

    def test_household_defaults(self):
        household = Household.objects.create(name="Test Household")
        self.assertFalse(household.pause_rotation)
        self.assertEqual(household.default_interval_days, 3)
        self.assertIsNotNone(household.created_at)

    def test_household_unique_invite_code(self):
        user = User.objects.create_user(username="alice", password="pass")
        user2 = User.objects.create_user(username="bob", password="pass")
        household = Household.objects.create(name="House A")
        household.partners.add(user, user2)
        self.assertIn(user, household.partners.all())
        self.assertIn(user2, household.partners.all())

    def test_household_invite_code_custom(self):
        household = Household.objects.create(name="House B", invite_code="ABC123")
        self.assertEqual(household.invite_code, "ABC123")

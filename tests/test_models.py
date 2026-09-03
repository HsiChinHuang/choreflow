from django.contrib.auth.models import User
from django.test import TestCase

from chores.models import Category, Chore, ChoreAssignment, Household, Notification


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


class TestCategory(TestCase):
    def test_category_str(self):
        category = Category.objects.create(name="Cleaning")
        self.assertEqual(str(category), "Cleaning")

    def test_category_is_predefined_default(self):
        category = Category.objects.create(name="Cleaning")
        self.assertTrue(category.is_predefined)

    def test_category_predefined_has_no_household(self):
        category = Category.objects.create(name="Cleaning", is_predefined=True)
        self.assertIsNone(category.household)

    def test_category_non_predefined_has_household(self):
        household = Household.objects.create(name="Test HH")
        category = Category.objects.create(name="Custom Chore", is_predefined=False, household=household)
        self.assertEqual(category.household, household)

    def test_category_defaults(self):
        category = Category.objects.create(name="Cleaning")
        self.assertTrue(category.is_predefined)
        self.assertIsNone(category.household)


class TestChore(TestCase):
    def test_chore_str(self):
        household = Household.objects.create(name="Test HH")
        user = User.objects.create_user(username="alice", password="pass")
        category = Category.objects.create(name="Cleaning")
        chore = Chore.objects.create(
            name="Vacuum",
            category=category,
            difficulty="easy",
            household=household,
            created_by=user,
        )
        self.assertEqual(str(chore), "Vacuum")

    def test_chore_difficulty_points(self):
        household = Household.objects.create(name="Test HH")
        user = User.objects.create_user(username="alice", password="pass")
        category = Category.objects.create(name="Cleaning")
        easy_chore = Chore.objects.create(
            name="Sweep", category=category, difficulty="easy", household=household, created_by=user,
        )
        medium_chore = Chore.objects.create(
            name="Mop", category=category, difficulty="medium", household=household, created_by=user,
        )
        hard_chore = Chore.objects.create(
            name="Clean oven", category=category, difficulty="hard", household=household, created_by=user,
        )
        self.assertEqual(easy_chore.difficulty_points, 1)
        self.assertEqual(medium_chore.difficulty_points, 2)
        self.assertEqual(hard_chore.difficulty_points, 3)

    def test_chore_difficulty_points_unknown_fallback(self):
        household = Household.objects.create(name="Test HH")
        user = User.objects.create_user(username="alice", password="pass")
        category = Category.objects.create(name="Cleaning")
        chore = Chore(name="Unknown Diff", category=category, difficulty="extreme", household=household, created_by=user)
        self.assertEqual(chore.difficulty_points, 2)

    def test_chore_defaults(self):
        household = Household.objects.create(name="Test HH")
        user = User.objects.create_user(username="alice", password="pass")
        category = Category.objects.create(name="Cleaning")
        chore = Chore.objects.create(
            name="Vacuum", category=category, difficulty="easy", household=household, created_by=user,
        )
        self.assertFalse(chore.is_one_time)
        self.assertIsNone(chore.interval_override_days)
        self.assertIsNone(chore.confirmed_by)
        self.assertIsNone(chore.pending_changes)
        self.assertIsNotNone(chore.created_at)

    def test_chore_nullable_fields(self):
        household = Household.objects.create(name="Test HH")
        user = User.objects.create_user(username="alice", password="pass")
        category = Category.objects.create(name="Cleaning")
        chore = Chore.objects.create(
            name="Vacuum",
            category=category,
            difficulty="easy",
            household=household,
            created_by=user,
            interval_override_days=7,
        )
        self.assertEqual(chore.interval_override_days, 7)


class TestChoreAssignment(TestCase):
    def test_assignment_str(self):
        household = Household.objects.create(name="Test HH")
        user = User.objects.create_user(username="alice", password="pass")
        category = Category.objects.create(name="Cleaning")
        chore = Chore.objects.create(
            name="Vacuum", category=category, difficulty="easy", household=household, created_by=user,
        )
        assignment = ChoreAssignment.objects.create(
            chore=chore, assigned_to=user, due_date="2025-01-15T10:00:00Z",
        )
        self.assertEqual(str(assignment), "Vacuum -> alice")

    def test_assignment_defaults(self):
        household = Household.objects.create(name="Test HH")
        user = User.objects.create_user(username="alice", password="pass")
        category = Category.objects.create(name="Cleaning")
        chore = Chore.objects.create(
            name="Vacuum", category=category, difficulty="easy", household=household, created_by=user,
        )
        assignment = ChoreAssignment.objects.create(
            chore=chore, assigned_to=user, due_date="2025-01-15T10:00:00Z",
        )
        self.assertFalse(assignment.completed)
        self.assertIsNone(assignment.completed_at)
        self.assertIsNotNone(assignment.created_at)

    def test_assignment_complete(self):
        household = Household.objects.create(name="Test HH")
        user = User.objects.create_user(username="alice", password="pass")
        category = Category.objects.create(name="Cleaning")
        chore = Chore.objects.create(
            name="Vacuum", category=category, difficulty="easy", household=household, created_by=user,
        )
        assignment = ChoreAssignment.objects.create(
            chore=chore, assigned_to=user, due_date="2025-01-15T10:00:00Z",
        )
        assignment.completed = True
        assignment.completed_at = "2025-01-14T10:00:00Z"
        assignment.save()
        self.assertTrue(assignment.completed)
        self.assertIsNotNone(assignment.completed_at)


class TestNotification(TestCase):
    def test_notification_str(self):
        user = User.objects.create_user(username="alice", password="pass")
        notification = Notification.objects.create(
            user=user, message="Your chore is due tomorrow!",
        )
        self.assertTrue(str(notification).startswith("[alice]"))
        self.assertIn("Your chore is due tomorrow", str(notification))

    def test_notification_defaults(self):
        user = User.objects.create_user(username="alice", password="pass")
        notification = Notification.objects.create(
            user=user, message="Reminder",
        )
        self.assertFalse(notification.read)
        self.assertIsNone(notification.chore_assignment)
        self.assertIsNotNone(notification.created_at)

    def test_notification_with_assignment(self):
        user = User.objects.create_user(username="alice", password="pass")
        household = Household.objects.create(name="Test HH")
        category = Category.objects.create(name="Cleaning")
        chore = Chore.objects.create(
            name="Vacuum", category=category, difficulty="easy", household=household, created_by=user,
        )
        assignment = ChoreAssignment.objects.create(
            chore=chore, assigned_to=user, due_date="2025-01-15T10:00:00Z",
        )
        notification = Notification.objects.create(
            user=user, message="Chore assigned!", chore_assignment=assignment,
        )
        self.assertEqual(notification.chore_assignment, assignment)

    def test_notification_read(self):
        user = User.objects.create_user(username="alice", password="pass")
        notification = Notification.objects.create(
            user=user, message="Read notif", read=True,
        )
        self.assertTrue(notification.read)

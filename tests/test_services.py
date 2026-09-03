# tests/test_services.py

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from chores.models import Category, Chore, ChoreAssignment, Household
from chores.services import assign_next, get_fair_assignee, get_total_points


class TestGetTotalPoints(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Test HH")
        self.alice = User.objects.create_user(username="alice", password="pass")
        self.bob = User.objects.create_user(username="bob", password="pass")
        self.household.partners.add(self.alice, self.bob)
        self.category = Category.objects.create(name="Cleaning")

    def test_returns_zero_for_user_with_no_completed(self):
        self.assertEqual(get_total_points(self.alice), 0)

    def test_counts_easy_points(self):
        chore = Chore.objects.create(
            name="Sweep",
            category=self.category,
            difficulty="easy",
            household=self.household,
            created_by=self.alice,
        )
        ChoreAssignment.objects.create(
            chore=chore,
            assigned_to=self.alice,
            due_date=timezone.now(),
            completed=True,
            completed_at=timezone.now(),
        )
        self.assertEqual(get_total_points(self.alice), 1)

    def test_counts_medium_points(self):
        chore = Chore.objects.create(
            name="Mop",
            category=self.category,
            difficulty="medium",
            household=self.household,
            created_by=self.alice,
        )
        ChoreAssignment.objects.create(
            chore=chore,
            assigned_to=self.alice,
            due_date=timezone.now(),
            completed=True,
            completed_at=timezone.now(),
        )
        self.assertEqual(get_total_points(self.alice), 2)

    def test_counts_hard_points(self):
        chore = Chore.objects.create(
            name="Clean oven",
            category=self.category,
            difficulty="hard",
            household=self.household,
            created_by=self.alice,
        )
        ChoreAssignment.objects.create(
            chore=chore,
            assigned_to=self.alice,
            due_date=timezone.now(),
            completed=True,
            completed_at=timezone.now(),
        )
        self.assertEqual(get_total_points(self.alice), 3)

    def test_only_counts_completed(self):
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            difficulty="hard",
            household=self.household,
            created_by=self.alice,
        )
        # Incomplete assignment should not count
        ChoreAssignment.objects.create(
            chore=chore,
            assigned_to=self.alice,
            due_date=timezone.now(),
            completed=False,
        )
        self.assertEqual(get_total_points(self.alice), 0)

    def test_counts_multiple_completed(self):
        chore1 = Chore.objects.create(
            name="Sweep",
            category=self.category,
            difficulty="easy",
            household=self.household,
            created_by=self.alice,
        )
        chore2 = Chore.objects.create(
            name="Mop",
            category=self.category,
            difficulty="medium",
            household=self.household,
            created_by=self.alice,
        )
        ChoreAssignment.objects.create(
            chore=chore1,
            assigned_to=self.alice,
            due_date=timezone.now(),
            completed=True,
            completed_at=timezone.now(),
        )
        ChoreAssignment.objects.create(
            chore=chore2,
            assigned_to=self.alice,
            due_date=timezone.now(),
            completed=True,
            completed_at=timezone.now(),
        )
        self.assertEqual(get_total_points(self.alice), 3)


class TestGetFairAssignee(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Test HH")
        self.alice = User.objects.create_user(username="alice", password="pass")
        self.bob = User.objects.create_user(username="bob", password="pass")
        self.household.partners.add(self.alice, self.bob)
        self.category = Category.objects.create(name="Cleaning")

    def test_returns_partner_with_lowest_points(self):
        # Alice has 0 points, Bob has 3 (hard chore completed)
        chore_bob = Chore.objects.create(
            name="Clean oven",
            category=self.category,
            difficulty="hard",
            household=self.household,
            created_by=self.alice,
        )
        ChoreAssignment.objects.create(
            chore=chore_bob,
            assigned_to=self.bob,
            due_date=timezone.now(),
            completed=True,
            completed_at=timezone.now(),
        )
        result = get_fair_assignee(self.household)
        self.assertEqual(result, self.alice)

    def test_returns_partner_with_lowest_points_alternate(self):
        # Alice has 3 points, Bob has 0
        chore_alice = Chore.objects.create(
            name="Clean oven",
            category=self.category,
            difficulty="hard",
            household=self.household,
            created_by=self.alice,
        )
        ChoreAssignment.objects.create(
            chore=chore_alice,
            assigned_to=self.alice,
            due_date=timezone.now(),
            completed=True,
            completed_at=timezone.now(),
        )
        result = get_fair_assignee(self.household)
        self.assertEqual(result, self.bob)

    def test_tie_breaks_randomly(self):
        # Both have 0 points — should return either
        result = get_fair_assignee(self.household)
        self.assertIn(result, [self.alice, self.bob])

    def test_returns_none_when_no_partners(self):
        Household.objects.create(name="Empty HH")
        result = get_fair_assignee(Household.objects.get(name="Empty HH"))
        self.assertIsNone(result)

    def test_only_considers_household_assignments(self):
        """Points from other households should not count."""
        other_household = Household.objects.create(name="Other HH")
        other_alice = User.objects.create_user(username="other_alice", password="pass")
        other_household.partners.add(other_alice)
        other_category = Category.objects.create(name="Other")
        other_chore = Chore.objects.create(
            name="Other chore",
            category=other_category,
            difficulty="hard",
            household=other_household,
            created_by=other_alice,
        )
        ChoreAssignment.objects.create(
            chore=other_chore,
            assigned_to=other_alice,
            due_date=timezone.now(),
            completed=True,
            completed_at=timezone.now(),
        )
        # other_alice has points in another household, but not in our household
        result = get_fair_assignee(self.household)
        self.assertIn(result, [self.alice, self.bob])

    def test_counts_all_difficulties_in_tie(self):
        # Alice: 1 (easy) + 2 (medium) = 3, Bob: 3 (hard) = 3, tie
        chore1 = Chore.objects.create(
            name="Sweep",
            category=self.category,
            difficulty="easy",
            household=self.household,
            created_by=self.alice,
        )
        chore2 = Chore.objects.create(
            name="Mop",
            category=self.category,
            difficulty="medium",
            household=self.household,
            created_by=self.alice,
        )
        chore3 = Chore.objects.create(
            name="Clean oven",
            category=self.category,
            difficulty="hard",
            household=self.household,
            created_by=self.alice,
        )
        ChoreAssignment.objects.create(
            chore=chore1,
            assigned_to=self.alice,
            due_date=timezone.now(),
            completed=True,
            completed_at=timezone.now(),
        )
        ChoreAssignment.objects.create(
            chore=chore2,
            assigned_to=self.alice,
            due_date=timezone.now(),
            completed=True,
            completed_at=timezone.now(),
        )
        ChoreAssignment.objects.create(
            chore=chore3,
            assigned_to=self.bob,
            due_date=timezone.now(),
            completed=True,
            completed_at=timezone.now(),
        )
        # Both have 3 points, tie
        result = get_fair_assignee(self.household)
        self.assertIn(result, [self.alice, self.bob])


class TestAssignNext(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Test HH", default_interval_days=3)
        self.alice = User.objects.create_user(username="alice", password="pass")
        self.bob = User.objects.create_user(username="bob", password="pass")
        self.household.partners.add(self.alice, self.bob)
        self.category = Category.objects.create(name="Cleaning")

    def test_returns_chore_assignment(self):
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            difficulty="easy",
            household=self.household,
            created_by=self.alice,
        )
        assignment = assign_next(chore)
        self.assertIsInstance(assignment, ChoreAssignment)
        self.assertEqual(assignment.chore, chore)

    def test_first_assignment_uses_fair_assignee(self):
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            difficulty="easy",
            household=self.household,
            created_by=self.alice,
        )
        assignment = assign_next(chore)
        # For first assignment, either partner is valid (both 0 points)
        self.assertIn(assignment.assigned_to, [self.alice, self.bob])

    def test_alternates_to_different_partner(self):
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            difficulty="easy",
            household=self.household,
            created_by=self.alice,
        )
        first = assign_next(chore)
        # Mark first as completed so it counts
        first.completed = True
        first.completed_at = timezone.now()
        first.save()
        second = assign_next(chore)
        self.assertNotEqual(second.assigned_to, first.assigned_to)

    def test_alternates_chain(self):
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            difficulty="easy",
            household=self.household,
            created_by=self.alice,
        )
        first = assign_next(chore)
        first.completed = True
        first.completed_at = timezone.now()
        first.save()

        second = assign_next(chore)
        self.assertNotEqual(second.assigned_to, first.assigned_to)
        second.completed = True
        second.completed_at = timezone.now()
        second.save()

        third = assign_next(chore)
        self.assertNotEqual(third.assigned_to, second.assigned_to)
        # Should be same as first
        self.assertEqual(third.assigned_to, first.assigned_to)

    def test_due_date_with_interval_override(self):
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            difficulty="easy",
            household=self.household,
            created_by=self.alice,
            interval_override_days=7,
        )
        first = assign_next(chore)
        first.completed = True
        first.completed_at = timezone.now()
        first.save()

        second = assign_next(chore)
        diff = (second.due_date - first.due_date).days
        self.assertEqual(diff, 7)

    def test_due_date_uses_household_default(self):
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            difficulty="easy",
            household=self.household,
            created_by=self.alice,
        )
        # default_interval_days = 3
        first = assign_next(chore)
        first.completed = True
        first.completed_at = timezone.now()
        first.save()

        second = assign_next(chore)
        diff = (second.due_date - first.due_date).days
        self.assertEqual(diff, 3)

    def test_first_assignment_due_date_is_now_plus_interval(self):
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            difficulty="easy",
            household=self.household,
            created_by=self.alice,
        )
        assignment = assign_next(chore)
        expected_min = timezone.now()
        expected_max = timezone.now() + timedelta(days=3)
        # due_date should be between now and now + interval
        self.assertGreaterEqual(assignment.due_date, expected_min)
        self.assertLessEqual(assignment.due_date, expected_max)

    def test_paused_rotation_raises_value_error(self):
        self.household.pause_rotation = True
        self.household.save()
        chore = Chore.objects.create(
            name="Vacuum",
            category=self.category,
            difficulty="easy",
            household=self.household,
            created_by=self.alice,
        )
        with self.assertRaises(ValueError):
            assign_next(chore)

    def test_first_assignment_no_partners_raises(self):
        empty_household = Household.objects.create(name="Empty HH")
        category = Category.objects.create(name="Empty")
        chore = Chore.objects.create(
            name="Vacuum",
            category=category,
            difficulty="easy",
            household=empty_household,
            created_by=User.objects.create_user(username="ghost", password="pass"),
        )
        with self.assertRaises(ValueError):
            assign_next(chore)

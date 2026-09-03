# chores/services.py

from datetime import timedelta

from django.utils import timezone
import random

from .models import ChoreAssignment


def get_total_points(user):
    """Calculate total difficulty points from completed assignments."""
    completed = ChoreAssignment.objects.filter(assigned_to=user, completed=True)
    total = 0
    for assignment in completed:
        total += assignment.chore.difficulty_points
    return total


def get_fair_assignee(household):
    """Pick partner with lowest total points (random tie-breaking).

    Used for first assignments and one-time chores.
    Returns the User with the lowest completed-assignment points.
    Random tie-breaking among tied partners.
    Returns None if the household has no partners.
    """
    partners = list(household.partners.all())
    if not partners:
        return None
    points = {partner: get_total_points(partner) for partner in partners}
    min_points = min(points.values())
    candidates = [p for p in partners if points[p] == min_points]
    return random.choice(candidates)


def assign_next(chore):
    """Determine the next assignee and due date for a chore.

    If the household has pause_rotation enabled, raises ValueError.

    If there is a last assignment, alternates to the other partner
    and uses previous due_date + interval.

    If no prior assignment exists (first), calls get_fair_assignee
    and uses now + interval.

    Interval is chore.interval_override_days if set, otherwise
    household.default_interval_days.

    Returns the newly created ChoreAssignment.
    """
    household = chore.household

    if household.pause_rotation:
        raise ValueError("Rotation is paused for this household")

    interval = (
        chore.interval_override_days
        if chore.interval_override_days is not None
        else household.default_interval_days
    )

    last_assignment = ChoreAssignment.objects.filter(chore=chore).order_by("-due_date").first()

    if last_assignment:
        # Alternate: pick the partner who was NOT last
        other_partners = [
            p
            for p in household.partners.all()
            if p != last_assignment.assigned_to
        ]
        if other_partners:
            next_assignee = other_partners[0]
        else:
            next_assignee = get_fair_assignee(household)
        next_due = last_assignment.due_date + timedelta(days=interval)
    else:
        # First assignment: use fair assignment logic
        next_assignee = get_fair_assignee(household)
        if next_assignee is None:
            raise ValueError("No partners available in this household")
        next_due = timezone.now() + timedelta(days=interval)

    return ChoreAssignment.objects.create(
        chore=chore,
        assigned_to=next_assignee,
        due_date=next_due,
    )

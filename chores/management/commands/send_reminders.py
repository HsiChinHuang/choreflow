import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from chores.models import ChoreAssignment, Notification


DEFAULT_OFFSET_DAYS = 2
OVERDUE_THRESHOLD_HOURS = 1


class Command(BaseCommand):
    help = "Send reminder and overdue notifications for chore assignments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--offset",
            type=int,
            default=DEFAULT_OFFSET_DAYS,
            help="Days before due date to send reminder (default: 2)",
        )

    def handle(self, *args, **options):
        offset_days = options["offset"]
        now = timezone.now()

        open_assignments = ChoreAssignment.objects.filter(
            completed=False,
        ).select_related("chore", "chore__category")

        created_count = 0

        for assignment in open_assignments:
            due_date = assignment.due_date

            # Check for upcoming reminder (within offset days before due)
            reminder_deadline = due_date - datetime.timedelta(days=offset_days)
            if reminder_deadline <= now <= due_date:
                exists = Notification.objects.filter(
                    user=assignment.assigned_to,
                    chore_assignment=assignment,
                    notification_type=Notification.REMINDER,
                ).exists()
                if not exists:
                    chore_name = assignment.chore.name
                    Notification.objects.create(
                        user=assignment.assigned_to,
                        message=f"{chore_name} is due in {offset_days} days",
                        chore_assignment=assignment,
                        notification_type=Notification.REMINDER,
                    )
                    created_count += 1
                    self.stdout.write(
                        f"  Created reminder for {assignment.assigned_to.username}: {chore_name}"
                    )

            # Check for overdue (past due date by 1+ hour)
            overdue_deadline = due_date + datetime.timedelta(hours=OVERDUE_THRESHOLD_HOURS)
            if now > overdue_deadline:
                exists = Notification.objects.filter(
                    user=assignment.assigned_to,
                    chore_assignment=assignment,
                    notification_type=Notification.OVERDUE,
                ).exists()
                if not exists:
                    chore_name = assignment.chore.name
                    Notification.objects.create(
                        user=assignment.assigned_to,
                        message=f"{chore_name} is overdue by {OVERDUE_THRESHOLD_HOURS} hour(s)",
                        chore_assignment=assignment,
                        notification_type=Notification.OVERDUE,
                    )
                    created_count += 1
                    self.stdout.write(
                        f"  Created overdue for {assignment.assigned_to.username}: {chore_name}"
                    )

        self.stdout.write(
            self.style.SUCCESS(f"Done. Created {created_count} notifications.")
        )

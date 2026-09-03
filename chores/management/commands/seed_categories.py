from django.core.management.base import BaseCommand
from chores.models import Category


PREDEFINED_CATEGORIES = [
    "Kitchen",
    "Bathroom",
    "Bedroom",
    "Living Room",
    "Outdoor",
    "Other",
]


class Command(BaseCommand):
    help = "Seed predefined categories into the database."

    def handle(self, *args, **options):
        created_count = 0
        for name in PREDEFINED_CATEGORIES:
            obj, created = Category.objects.get_or_create(
                name=name,
                defaults={"is_predefined": True, "household": None},
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created: {name}")
            else:
                self.stdout.write(f"  Exists: {name}")
        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created_count}/{len(PREDEFINED_CATEGORIES)} categories.")
        )

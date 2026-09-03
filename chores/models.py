# chores/models.py

from django.contrib.auth.models import User
from django.db import models
import random
import string


class Household(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    partners = models.ManyToManyField(User, related_name="households")
    pause_rotation = models.BooleanField(default=False)
    default_interval_days = models.IntegerField(default=3)
    invite_code = models.CharField(max_length=20, unique=True, blank=True)

    def __str__(self):
        return self.name

    @classmethod
    def generate_invite_code(cls, length=8):
        """Generate a unique alphanumeric invite code of specified length."""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(chars, k=length))
            if not cls.objects.filter(invite_code=code).exists():
                return code

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = self.generate_invite_code()
        super().save(*args, **kwargs)


class Category(models.Model):
    name = models.CharField(max_length=100)
    is_predefined = models.BooleanField(default=True)
    household = models.ForeignKey(
        "Household", on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return self.name


class Chore(models.Model):
    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    ]

    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    interval_override_days = models.IntegerField(null=True, blank=True)
    is_one_time = models.BooleanField(default=False)
    household = models.ForeignKey(Household, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_chores")
    confirmed_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="confirmed_chores")
    pending_changes = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def difficulty_points(self):
        return {"easy": 1, "medium": 2, "hard": 3}.get(self.difficulty, 2)


class ChoreAssignment(models.Model):
    chore = models.ForeignKey(Chore, on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chore_assignments")
    due_date = models.DateTimeField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.chore.name} -> {self.assigned_to.username}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    chore_assignment = models.ForeignKey(
        ChoreAssignment, on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return f"[{self.user.username}] {self.message[:50]}"

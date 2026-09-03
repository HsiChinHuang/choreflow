# chores/models.py

from django.contrib.auth.models import User
from django.db import models
import uuid


class Household(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    partners = models.ManyToManyField(User, related_name="households")
    pause_rotation = models.BooleanField(default=False)
    default_interval_days = models.IntegerField(default=3)
    invite_code = models.CharField(max_length=20, unique=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = uuid.uuid4().hex[:20]
        super().save(*args, **kwargs)

# chores/admin.py

from django.contrib import admin

from .models import Household


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "pause_rotation", "default_interval_days")
    list_filter = ("pause_rotation", "created_at")
    search_fields = ("name", "invite_code")
    readonly_fields = ("created_at", "invite_code")

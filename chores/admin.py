# chores/admin.py

from django.contrib import admin

from .models import Category, Chore, ChoreAssignment, Household, Notification


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "pause_rotation", "default_interval_days")
    list_filter = ("pause_rotation", "created_at")
    search_fields = ("name", "invite_code")
    readonly_fields = ("created_at", "invite_code")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_predefined", "household")
    list_filter = ("is_predefined", "household")
    search_fields = ("name",)


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "difficulty", "household", "is_one_time", "created_at")
    list_filter = ("difficulty", "is_one_time", "category", "household")
    search_fields = ("name", "category__name")
    readonly_fields = ("created_at",)


@admin.register(ChoreAssignment)
class ChoreAssignmentAdmin(admin.ModelAdmin):
    list_display = ("chore", "assigned_to", "due_date", "completed")
    list_filter = ("completed", "due_date", "chore__category")
    search_fields = ("chore__name", "assigned_to__username")
    readonly_fields = ("created_at",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "created_at", "read")
    list_filter = ("read", "created_at")
    search_fields = ("user__username", "message")
    readonly_fields = ("created_at",)

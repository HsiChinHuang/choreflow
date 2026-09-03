from django.template.loader import render_to_string
from pathlib import Path
from django.conf import settings
import pytest


def test_base_template_renders():
    html = render_to_string("base.html")
    assert "<!DOCTYPE html>" in html
    assert "ChoreFlow" in html


def test_base_template_has_bootstrap():
    html = render_to_string("base.html")
    assert "cdn.jsdelivr.net/npm/bootstrap" in html


def test_base_template_defines_blocks():
    """Verify base.html defines title, content, and extra_js blocks."""
    base_template_path = settings.BASE_DIR / "chores" / "templates" / "base.html"
    source = base_template_path.read_text()
    assert "{% block title %}" in source
    assert "{% block content %}" in source
    assert "{% block extra_js %}" in source


def test_base_template_has_navbar():
    html = render_to_string("base.html")
    assert 'navbar' in html
    assert "ChoreFlow" in html


# ─── Issue #47: Base template with navbar and Bootstrap ───────────────────────

class TestBaseTemplateIssues:
    """Tests for issues #47 (base template), #48 (dashboard), #49 (chore_list),
    #50 (chore_form), #51 (fairness_stats), #52 (household_settings),
    #53 (notification_list)."""

    def test_base_has_bootstrap_css(self):
        html = render_to_string("base.html")
        assert "bootstrap.min.css" in html

    def test_base_has_bootstrap_js(self):
        html = render_to_string("base.html")
        assert "bootstrap.bundle.min.js" in html

    def test_base_has_messages_block(self):
        base_template_path = settings.BASE_DIR / "chores" / "templates" / "base.html"
        source = base_template_path.read_text()
        assert "messages" in source
        assert "alert" in source

    def test_base_has_dashboard_link(self):
        base_template_path = settings.BASE_DIR / "chores" / "templates" / "base.html"
        source = base_template_path.read_text()
        assert "Dashboard" in source

    def test_base_has_chores_link(self):
        base_template_path = settings.BASE_DIR / "chores" / "templates" / "base.html"
        source = base_template_path.read_text()
        assert "Chores" in source

    def test_base_has_fairness_link(self):
        base_template_path = settings.BASE_DIR / "chores" / "templates" / "base.html"
        source = base_template_path.read_text()
        assert "Fairness" in source

    def test_base_has_notifications_link(self):
        base_template_path = settings.BASE_DIR / "chores" / "templates" / "base.html"
        source = base_template_path.read_text()
        assert "Notifications" in source

    def test_base_has_settings_link(self):
        base_template_path = settings.BASE_DIR / "chores" / "templates" / "base.html"
        source = base_template_path.read_text()
        assert "Settings" in source

    def test_base_has_logout(self):
        base_template_path = settings.BASE_DIR / "chores" / "templates" / "base.html"
        source = base_template_path.read_text()
        assert "Logout" in source

    def test_base_has_unread_badge(self):
        base_template_path = settings.BASE_DIR / "chores" / "templates" / "base.html"
        source = base_template_path.read_text()
        assert "unread_count" in source or "badge" in source

    def test_base_has_content_block(self):
        html = render_to_string("base.html")
        assert "container mt-4" in html


# ─── Issue #48: Dashboard template ───────────────────────────────────────────

class TestDashboardTemplate:
    def test_dashboard_has_today_column(self):
        html = render_to_string("chores/dashboard.html", {
            'today': [], 'upcoming': [], 'overdue': [], 'unread_count': 0,
        })
        assert "Today" in html

    def test_dashboard_has_upcoming_column(self):
        html = render_to_string("chores/dashboard.html", {
            'today': [], 'upcoming': [], 'overdue': [], 'unread_count': 0,
        })
        assert "Upcoming" in html

    def test_dashboard_has_overdue_column(self):
        html = render_to_string("chores/dashboard.html", {
            'today': [], 'upcoming': [], 'overdue': [], 'unread_count': 0,
        })
        assert "Overdue" in html

    def test_overdue_card_has_red_border(self):
        html = render_to_string("chores/dashboard.html", {
            'today': [], 'upcoming': [], 'overdue': [], 'unread_count': 0,
        })
        assert "border-danger" in html

    def test_dashboard_has_complete_buttons(self):
        partial_path = settings.BASE_DIR / "chores" / "templates" / "partials" / "chore_card.html"
        source = partial_path.read_text()
        assert "complete-form" in source


# ─── Issue #49: Chore list template ──────────────────────────────────────────

class TestChoreListTemplate:
    def test_chore_list_has_edit_button(self):
        list_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "chore_list.html"
        source = list_path.read_text()
        assert "Edit" in source

    def test_chore_list_has_delete_button(self):
        list_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "chore_list.html"
        source = list_path.read_text()
        assert "Delete" in source

    def test_chore_list_has_pending_changes_badge(self):
        list_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "chore_list.html"
        source = list_path.read_text()
        assert "Pending changes" in source

    def test_chore_list_has_confirm_button_for_pending(self):
        list_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "chore_list.html"
        source = list_path.read_text()
        assert "Confirm" in source

    def test_chore_list_has_new_chore_button(self):
        html = render_to_string("chores/chore_list.html", {
            'chores': [], 'household': None,
        })
        assert "New Chore" in html


# ─── Issue #50: Chore form template ──────────────────────────────────────────

class TestChoreFormTemplate:
    def test_chore_form_has_name_field(self):
        html = render_to_string("chores/chore_form.html", {
            'form': None, 'categories': [], 'household': None,
            'error': None, 'is_create': True,
            'is_edit': False, 'is_pending': False, 'can_apply_directly': True,
        })
        assert "Name" in html

    def test_chore_form_has_category_dropdown(self):
        html = render_to_string("chores/chore_form.html", {
            'form': None, 'categories': [], 'household': None,
            'error': None, 'is_create': True,
            'is_edit': False, 'is_pending': False, 'can_apply_directly': True,
        })
        assert "Category" in html

    def test_chore_form_has_difficulty_select(self):
        html = render_to_string("chores/chore_form.html", {
            'form': None, 'categories': [], 'household': None,
            'error': None, 'is_create': True,
            'is_edit': False, 'is_pending': False, 'can_apply_directly': True,
        })
        assert "Easy" in html and "Medium" in html and "Hard" in html

    def test_chore_form_has_interval_override(self):
        html = render_to_string("chores/chore_form.html", {
            'form': None, 'categories': [], 'household': None,
            'error': None, 'is_create': True,
            'is_edit': False, 'is_pending': False, 'can_apply_directly': True,
        })
        assert "Interval Override" in html

    def test_chore_form_has_submit_button(self):
        html = render_to_string("chores/chore_form.html", {
            'form': None, 'categories': [], 'household': None,
            'error': None, 'is_create': True,
            'is_edit': False, 'is_pending': False, 'can_apply_directly': True,
        })
        assert "Create Chore" in html

    def test_chore_form_shows_pending_note(self):
        html = render_to_string("chores/chore_form.html", {
            'form': None, 'categories': [], 'household': None,
            'error': None, 'is_create': False,
            'is_edit': True, 'is_pending': True, 'can_apply_directly': False,
        })
        assert "pending" in html.lower()


# ─── Issue #51: Fairness stats template ──────────────────────────────────────

class TestFairnessStatsTemplate:
    def test_fairness_has_partner_panels(self):
        html = render_to_string("chores/fairness_stats.html", {
            'partner_data': [], 'history': [], 'household': None,
        })
        assert "Fairness Stats" in html

    def test_fairness_has_progress_bars(self):
        fairness_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "fairness_stats.html"
        source = fairness_path.read_text()
        assert "progress" in source

    def test_fairness_has_history_table(self):
        html = render_to_string("chores/fairness_stats.html", {
            'partner_data': [], 'history': [], 'household': None,
        })
        assert "Recent Activity" in html

    def test_fairness_has_difficulty_badges(self):
        fairness_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "fairness_stats.html"
        source = fairness_path.read_text()
        assert "badge" in source


# ─── Issue #52: Household settings template ──────────────────────────────────

class TestHouseholdSettingsTemplate:
    def test_settings_has_name_field(self):
        settings_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "household_settings.html"
        source = settings_path.read_text()
        assert "Household Name" in source

    def test_settings_has_interval_field(self):
        settings_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "household_settings.html"
        source = settings_path.read_text()
        assert "Default Interval" in source

    def test_settings_has_invite_code(self):
        settings_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "household_settings.html"
        source = settings_path.read_text()
        assert 'invite_code' in source

    def test_settings_has_copy_button(self):
        settings_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "household_settings.html"
        source = settings_path.read_text()
        assert "copyInviteCode" in source or "Copy" in source

    def test_settings_has_pause_toggle(self):
        settings_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "household_settings.html"
        source = settings_path.read_text()
        assert "Pause" in source or "rotation" in source.lower()


# ─── Issue #53: Notification list template ───────────────────────────────────

class TestNotificationListTemplate:
    def test_notification_list_has_unread_dot(self):
        notif_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "notification_list.html"
        source = notif_path.read_text()
        assert "unread-dot" in source

    def test_notification_list_has_list_group(self):
        html = render_to_string("chores/notification_list.html", {
            'notifications': [],
        })
        assert "list-group" in html

    def test_notification_list_has_click_handler(self):
        notif_path = settings.BASE_DIR / "chores" / "templates" / "chores" / "notification_list.html"
        source = notif_path.read_text()
        assert "notification-item" in source

    def test_notification_list_shows_timestamp(self):
        html = render_to_string("chores/notification_list.html", {
            'notifications': [],
        })
        assert "text-muted" in html

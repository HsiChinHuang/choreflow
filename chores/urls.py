# chores/urls.py

from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page='/login/',
    ), name='logout'),
    path('signup/', views.signup, name='signup'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Chore CRUD
    path('chores/', views.chore_list, name='chore_list'),
    path('chores/new/', views.chore_create, name='chore_create'),
    path('chores/<int:pk>/edit/', views.chore_update, name='chore_update'),
    path('chores/<int:pk>/delete/', views.chore_delete, name='chore_delete'),
    path('chores/<int:pk>/confirm/', views.chore_confirm, name='chore_confirm'),

    # Assignments
    path('assignments/', views.assignment_list, name='assignment_list'),
    path('assignments/<int:pk>/complete/', views.assignment_complete, name='assignment_complete'),

    # One-time chores
    path('one-time/new/', views.one_time_create, name='one_time_create'),

    # Household & settings
    path('household/', views.household_settings, name='household_settings'),
    path('household/pause/', views.pause_rotation, name='pause_rotation'),
    path('categories/', views.category_manage, name='category_manage'),

    # Fairness
    path('fairness/', views.fairness_stats, name='fairness_stats'),

    # Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/read/', views.notification_read, name='notification_read'),
]

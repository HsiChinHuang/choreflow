# chores/views.py

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import Category, Chore, ChoreAssignment, Household


# --- Issue #22: Signup view (basic) ---

def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        invite_code = request.POST.get('invite_code', '').strip()

        if not username or not password:
            return render(request, 'registration/signup.html', {
                'error': 'Username and password are required.',
                'invite_code': invite_code,
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'registration/signup.html', {
                'error': 'A user with that username already exists.',
                'invite_code': invite_code,
            })

        # Issue #25: Check invite code first
        if invite_code:
            try:
                household = Household.objects.get(invite_code=invite_code)
            except ObjectDoesNotExist:
                return render(request, 'registration/signup.html', {
                    'error': 'Invalid invite code. Please check and try again.',
                    'invite_code': invite_code,
                })
            # Issue #25: Join existing household
            user = User.objects.create_user(username=username, password=password)
            household.partners.add(user)
            login(request, user)
            return redirect('dashboard')
        else:
            # Issue #24: Create new household
            user = User.objects.create_user(username=username, password=password)
            household = Household.objects.create(name=f"{username}'s Household")
            household.partners.add(user)
            login(request, user)
            return redirect('dashboard')

    return render(request, 'registration/signup.html')


# --- Issue #23: Login/Logout via Django auth views ---
# (handled by Django's LoginView/LogoutView, no custom view needed)

def logged_out(request):
    return render(request, 'registration/logged_out.html')


# --- Issue #26: Generate unique invite code for household ---
# (generate_invite_code is a model method on Household)


# --- Dashboard ---

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, "chores/dashboard.html")


# --- Household settings view ---

def household_settings(request):
    household = request.user.households.first()
    if not household:
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'regenerate_code':
            new_code = Household.generate_invite_code()
            household.invite_code = new_code
            household.save()
            return redirect('household_settings')

    return render(request, 'chores/household_settings.html', {
        'household': household,
    })


def pause_rotation(request):
    household = request.user.households.first()
    if not household:
        return redirect('dashboard')

    household.pause_rotation = not household.pause_rotation
    household.save()
    return redirect('household_settings')


# --- Chore CRUD ---

def chore_list(request):
    household = request.user.households.first()
    if not household:
        return redirect('dashboard')
    chores = Chore.objects.filter(household=household)
    return render(request, 'chores/chore_list.html', {'chores': chores})


def chore_create(request):
    household = request.user.households.first()
    if not household:
        return redirect('dashboard')

    categories = Category.objects.filter(household=household) | Category.objects.filter(household__isnull=True)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        difficulty = request.POST.get('difficulty', 'medium')
        is_one_time = request.POST.get('is_one_time') == 'on'
        interval_override = request.POST.get('interval_override_days')

        if not name or not category_id:
            return render(request, 'chores/chore_form.html', {
                'categories': categories,
                'household': household,
                'error': 'Name and category are required.',
            })

        category = Category.objects.get(id=category_id)
        chore = Chore.objects.create(
            name=name,
            category=category,
            difficulty=difficulty,
            household=household,
            created_by=request.user,
            is_one_time=is_one_time,
        )
        if interval_override:
            chore.interval_override_days = int(interval_override)
            chore.save()

        return redirect('chore_list')

    return render(request, 'chores/chore_form.html', {
        'categories': categories,
        'household': household,
    })


def chore_update(request, pk):
    chore = get_object_or_404(Chore, pk=pk)
    if chore.household not in request.user.households.all():
        return redirect('dashboard')

    categories = Category.objects.filter(household=chore.household) | Category.objects.filter(household__isnull=True)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        difficulty = request.POST.get('difficulty', 'medium')
        interval_override = request.POST.get('interval_override_days')

        if not name or not category_id:
            return render(request, 'chores/chore_form.html', {
                'categories': categories,
                'household': chore.household,
                'error': 'Name and category are required.',
            })

        category = Category.objects.get(id=category_id)

        # Save pending changes for partner confirmation
        pending = {
            'name': name,
            'category': category_id,
            'difficulty': difficulty,
        }
        if interval_override:
            pending['interval_override_days'] = int(interval_override)

        chore.name = name
        chore.category = category
        chore.difficulty = difficulty
        if interval_override:
            chore.interval_override_days = int(interval_override)
        chore.pending_changes = pending
        chore.confirmed_by = None
        chore.save()

        return redirect('chore_list')

    return render(request, 'chores/chore_form.html', {
        'categories': categories,
        'household': chore.household,
        'chore': chore,
    })


def chore_delete(request, pk):
    chore = get_object_or_404(Chore, pk=pk)
    if chore.household not in request.user.households.all():
        return redirect('dashboard')
    chore.delete()
    return redirect('chore_list')


def chore_confirm(request, pk):
    chore = get_object_or_404(Chore, pk=pk)
    if chore.household not in request.user.households.all():
        return redirect('dashboard')

    if request.method == 'POST' and chore.pending_changes:
        changes = chore.pending_changes
        chore.name = changes.get('name', chore.name)
        if 'category' in changes:
            chore.category = Category.objects.get(id=changes['category'])
        chore.difficulty = changes.get('difficulty', chore.difficulty)
        if 'interval_override_days' in changes:
            chore.interval_override_days = int(changes['interval_override_days'])
        chore.confirmed_by = request.user
        chore.pending_changes = None
        chore.save()

    return redirect('chore_list')


# --- Assignments ---

def assignment_list(request):
    household = request.user.households.first()
    if not household:
        return redirect('dashboard')
    assignments = ChoreAssignment.objects.filter(
        assigned_to=request.user
    ).select_related('chore', 'chore__category').order_by('-due_date')
    return render(request, 'chores/assignment_list.html', {
        'assignments': assignments,
    })


def assignment_complete(request, pk):
    assignment = get_object_or_404(ChoreAssignment, pk=pk)
    if assignment.assigned_to != request.user:
        return redirect('dashboard')
    assignment.completed = True
    assignment.completed_at = timezone.now()
    assignment.save()
    return redirect('dashboard')


# --- One-time chores ---

def one_time_create(request):
    household = request.user.households.first()
    if not household:
        return redirect('dashboard')
    return render(request, 'chores/one_time_form.html', {'household': household})


# --- Fairness stats ---

def fairness_stats(request):
    household = request.user.households.first()
    if not household:
        return redirect('dashboard')

    partners = list(household.partners.all())
    partner_data = []
    for partner in partners:
        completed = ChoreAssignment.objects.filter(
            assigned_to=partner, completed=True
        )
        total_points = sum(a.chore.difficulty_points for a in completed)
        partner_data.append({
            'user': partner,
            'points': total_points,
            'completed_count': completed.count(),
        })

    return render(request, 'chores/fairness_stats.html', {
        'household': household,
        'partner_data': partner_data,
    })


# --- Notifications ---

def notification_list(request):
    notifications = request.user.notifications.order_by('-created_at')
    return render(request, 'chores/notification_list.html', {
        'notifications': notifications,
    })


def notification_read(request, pk):
    notification = get_object_or_404(request.user.notifications, pk=pk)
    notification.read = True
    notification.save()
    return redirect('notification_list')


# --- Category management ---

def category_manage(request):
    household = request.user.households.first()
    if not household:
        return redirect('dashboard')

    categories = Category.objects.filter(
        household=household
    ) | Category.objects.filter(household__isnull=True)

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'add':
            name = request.POST.get('name', '').strip()
            if name and request.POST.get('is_custom') == 'on':
                Category.objects.create(name=name, is_predefined=False, household=household)
        elif action == 'delete':
            cat_id = request.POST.get('category_id')
            if cat_id:
                cat = get_object_or_404(Category, id=cat_id)
                if not cat.is_predefined and cat.household == household:
                    cat.delete()

    predefined = Category.objects.filter(is_predefined=True, household__isnull=True)
    custom = Category.objects.filter(household=household)

    return render(request, 'chores/category_manage.html', {
        'household': household,
        'custom': custom,
        'predefined': predefined,
    })

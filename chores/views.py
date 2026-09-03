# chores/views.py

from datetime import datetime, timedelta
from django.utils.timezone import make_aware

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ChoreForm
from .models import Category, Chore, ChoreAssignment, Household
from .services import assign_next, get_fair_assignee, get_total_points


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
    household = request.user.households.first()
    if not household:
        return render(request, "chores/dashboard.html", {
            'today': [], 'upcoming': [], 'overdue': [], 'unread_count': 0,
        })

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59, microsecond=999999)

    open_assignments = ChoreAssignment.objects.filter(
        chore__household=household,
        assigned_to=request.user,
        completed=False,
    ).select_related('chore', 'chore__category')

    today = []
    upcoming = []
    overdue = []

    for a in open_assignments:
        due_today = a.due_date >= today_start and a.due_date <= today_end
        if a.due_date < today_start:
            overdue.append(a)
        elif due_today:
            today.append(a)
        else:
            upcoming.append(a)

    today.sort(key=lambda a: a.due_date)
    upcoming.sort(key=lambda a: a.due_date)
    overdue.sort(key=lambda a: a.due_date)

    unread_count = request.user.notifications.filter(read=False).count()

    return render(request, "chores/dashboard.html", {
        'today': today,
        'upcoming': upcoming,
        'overdue': overdue,
        'unread_count': unread_count,
    })


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
        elif action == 'update_settings':
            name = request.POST.get('name', '').strip()
            interval_str = request.POST.get('default_interval_days', '')
            if name:
                household.name = name
            if interval_str:
                try:
                    household.default_interval_days = int(interval_str)
                except ValueError:
                    pass
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


def _auto_assign_chore(chore, household):
    """Auto-generate the first assignment for a new chore."""
    partners = list(household.partners.all())
    if not partners:
        return
    # Assign to the first partner (round-robin style)
    assigned_to = partners[0]
    due_date = timezone.now() + timedelta(days=chore.interval_override_days or household.default_interval_days)
    ChoreAssignment.objects.create(
        chore=chore,
        assigned_to=assigned_to,
        due_date=due_date,
    )


# --- Chore CRUD (Issues #30-#34) ---

def chore_list(request):
    """Issue #34: List all chores for current household (is_one_time=False)."""
    if not request.user.is_authenticated:
        return redirect('login')
    household = request.user.households.first()
    if not household:
        return redirect('dashboard')
    chores = Chore.objects.filter(
        household=household,
        is_one_time=False,
    ).select_related('category', 'created_by', 'confirmed_by')
    return render(request, 'chores/chore_list.html', {
        'chores': chores,
        'household': household,
    })


def chore_create(request):
    """Issue #30: Form for recurring chore creation."""
    if not request.user.is_authenticated:
        return redirect('login')
    household = request.user.households.first()
    if not household:
        return redirect('dashboard')

    categories = Category.objects.filter(household=household) | Category.objects.filter(household__isnull=True)
    partners_count = household.partners.count()

    if request.method == 'POST':
        form = ChoreForm(request.POST, categories=categories, household=household)
        if form.is_valid():
            chore = form.save(commit=False)
            chore.household = household
            chore.created_by = request.user
            chore.is_one_time = False

            # If multiple partners, set confirmed_by=None (pending confirmation)
            if partners_count > 1:
                chore.confirmed_by = None

            chore.save()

            # Auto-generate first assignment
            _auto_assign_chore(chore, household)

            return redirect('chore_list')
        else:
            error = form.errors.as_text()
    else:
        form = ChoreForm(categories=categories, household=household)
        error = None

    return render(request, 'chores/chore_form.html', {
        'form': form,
        'categories': categories,
        'household': household,
        'error': error,
        'is_create': True,
    })


def chore_update(request, pk):
    """Issue #31: Edit form with pending changes for non-creator/multi-partner."""
    chore = get_object_or_404(Chore, pk=pk)
    if chore.household not in request.user.households.all():
        return redirect('dashboard')

    household = chore.household
    categories = Category.objects.filter(household=household) | Category.objects.filter(household__isnull=True)
    partners_count = household.partners.count()
    is_creator = chore.created_by == request.user
    is_single_partner = partners_count == 1

    # Creator or single-partner household applies changes directly
    can_apply_directly = is_creator or is_single_partner

    if request.method == 'POST':
        form = ChoreForm(
            request.POST, categories=categories, household=household, instance=chore
        )
        # Save original values before form.is_valid() (which modifies instance)
        original_name = chore.name
        original_category = chore.category
        original_difficulty = chore.difficulty
        original_interval = chore.interval_override_days
        if form.is_valid():
            if can_apply_directly:
                # Apply changes directly (creator or single partner)
                form.save()
            else:
                # Save as pending changes (not the creator)
                # NOTE: form.is_valid() modifies chore.name via instance, so we restore original values
                cleaned = form.cleaned_data
                pending = {
                    'name': cleaned['name'],
                    'category': cleaned['category'].id,
                    'difficulty': cleaned.get('difficulty', original_difficulty),
                }
                if cleaned.get('interval_override_days') is not None:
                    pending['interval_override_days'] = cleaned['interval_override_days']

                # Restore original values (form.is_valid() modified the instance)
                chore.name = original_name
                chore.category = original_category
                chore.difficulty = original_difficulty
                chore.interval_override_days = original_interval
                chore.pending_changes = pending
                chore.confirmed_by = None
                chore.save()
            return redirect('chore_list')
        else:
            error = form.errors.as_text()
    else:
        form = ChoreForm(
            categories=categories,
            household=household,
            instance=chore,
            initial={
                'interval_override_days': chore.interval_override_days,
                'category': chore.category.id,
            },
        )
        error = None

    return render(request, 'chores/chore_form.html', {
        'form': form,
        'categories': categories,
        'household': household,
        'chore': chore,
        'error': error,
        'is_edit': True,
        'is_pending': chore.pending_changes is not None,
        'can_apply_directly': can_apply_directly,
    })


@require_POST
def chore_delete(request, pk):
    """Issue #33: Delete chore and all assignments. POST-only."""
    chore = get_object_or_404(Chore, pk=pk)
    if chore.household not in request.user.households.all():
        return redirect('dashboard')
    chore.delete()
    return redirect('chore_list')


def chore_confirm(request, pk):
    """Issue #32: Show current values and proposed changes from pending_changes."""
    chore = get_object_or_404(Chore, pk=pk)
    if chore.household not in request.user.households.all():
        return redirect('dashboard')

    household = chore.household

    if not chore.pending_changes:
        return redirect('chore_list')

    is_proposer = chore.created_by == request.user
    proposer = chore.created_by

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'confirm' and not is_proposer:
            # Partner (not proposer) confirms: apply changes, set confirmed_by, clear pending
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

        elif action == 'reject' and not is_proposer:
            # Partner (not proposer) rejects: clear pending_changes
            chore.pending_changes = None
            chore.save()
            return redirect('chore_list')

    return render(request, 'chores/chore_confirm.html', {
        'chore': chore,
        'pending_changes': chore.pending_changes,
        'proposer': proposer,
        'current_user': request.user,
        'household': household,
    })


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

    # If recurring and rotation not paused, create next assignment
    if not assignment.chore.is_one_time:
        household = assignment.chore.household
        if not household.pause_rotation:
            try:
                assign_next(assignment.chore)
            except ValueError:
                pass

    return redirect('dashboard')


# --- One-time chores ---

def one_time_create(request):
    if not request.user.is_authenticated:
        return redirect('login')
    household = request.user.households.first()
    if not household:
        return redirect('dashboard')

    categories = Category.objects.filter(household=household) | Category.objects.filter(household__isnull=True)
    partners_count = household.partners.count()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        difficulty = request.POST.get('difficulty', 'medium')
        due_date_str = request.POST.get('due_date', '')

        errors = []
        if not name:
            errors.append('Name is required.')
        if not category_id:
            errors.append('Category is required.')
            category = None
        else:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                errors.append('Invalid category selected.')
                category = None

        if difficulty not in dict(Chore.DIFFICULTY_CHOICES):
            difficulty = 'medium'

        if due_date_str:
            try:
                naive_dt = datetime.strptime(due_date_str, '%Y-%m-%d')
                due_date = make_aware(naive_dt)
            except ValueError:
                errors.append('Invalid date format.')
                due_date = timezone.now()
        else:
            due_date = timezone.now()

        if not errors:
            chore = Chore.objects.create(
                name=name,
                category=category,
                difficulty=difficulty,
                is_one_time=True,
                household=household,
                created_by=request.user,
            )

            # If multiple partners, set confirmed_by=None (pending confirmation)
            if partners_count > 1:
                chore.confirmed_by = None
                chore.save()

            # Auto-assign using fair assignment
            assignee = get_fair_assignee(household)
            if assignee:
                ChoreAssignment.objects.create(
                    chore=chore,
                    assigned_to=assignee,
                    due_date=due_date,
                )

            return redirect('chore_list')

        error = ' '.join(errors)
    else:
        error = None
        due_date = timezone.now().strftime('%Y-%m-%d')

    return render(request, 'chores/one_time_form.html', {
        'form': {'due_date': due_date} if request.method == 'POST' else {'due_date': timezone.now().strftime('%Y-%m-%d')},
        'categories': categories,
        'household': household,
        'error': error,
    })


# --- Fairness stats ---

def fairness_stats(request):
    if not request.user.is_authenticated:
        return redirect('login')
    household = request.user.households.first()
    if not household:
        return redirect('dashboard')

    partners = list(household.partners.all())
    partner_data = []
    for partner in partners:
        total_points = get_total_points(partner)
        completed = ChoreAssignment.objects.filter(
            assigned_to=partner, completed=True
        )
        partner_data.append({
            'user': partner,
            'points': total_points,
            'completed_count': completed.count(),
        })

    history = ChoreAssignment.objects.filter(
        completed=True
    ).select_related('chore', 'assigned_to', 'chore__category').order_by('-completed_at')[:20]

    return render(request, 'chores/fairness_stats.html', {
        'household': household,
        'partner_data': partner_data,
        'history': history,
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

PREDEFINED_CATEGORY_NAMES = frozenset([
    "Kitchen", "Bathroom", "Bedroom", "Living Room", "Outdoor", "Other",
])


def category_manage(request):
    if not request.user.is_authenticated:
        return redirect('login')

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
            is_custom = request.POST.get('is_custom') == 'on'
            if name:
                if is_custom:
                    if name not in PREDEFINED_CATEGORY_NAMES:
                        Category.objects.create(
                            name=name,
                            is_predefined=False,
                            household=household,
                        )
                else:
                    existing = Category.objects.filter(
                        household__isnull=True, is_predefined=True, name=name
                    )
                    if not existing.exists():
                        Category.objects.create(
                            name=name,
                            is_predefined=True,
                            household=None,
                        )
        elif action == 'delete':
            cat_id = request.POST.get('category_id')
            if cat_id:
                cat = get_object_or_404(Category, id=cat_id)
                if (
                    not cat.is_predefined
                    and cat.household == household
                    and not Chore.objects.filter(category=cat).exists()
                ):
                    cat.delete()
        return redirect('category_manage')

    predefined = Category.objects.filter(is_predefined=True, household__isnull=True)
    custom = Category.objects.filter(household=household)

    return render(request, 'chores/category_manage.html', {
        'household': household,
        'custom': custom,
        'predefined': predefined,
    })

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from chores.models import Category, Chore, ChoreAssignment, Household, Notification


class TestSignupView(TestCase):
    """Issue #22: Implement user signup view"""

    def setUp(self):
        self.client = Client()

    def test_signup_page_loads(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign Up')
        self.assertTemplateUsed(response, 'registration/signup.html')

    def test_signup_creates_user(self):
        """POST with valid username and password creates a User and redirects to dashboard."""
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'password': 'testpass123',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_signup_redirects_to_dashboard(self):
        """After signup, user is redirected to dashboard."""
        self.client.post(reverse('signup'), {
            'username': 'redirectuser',
            'password': 'testpass123',
        })
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_signup_rejects_empty_username(self):
        response = self.client.post(reverse('signup'), {
            'username': '',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'required')

    def test_signup_rejects_empty_password(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'password': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'required')

    def test_signup_rejects_duplicate_username(self):
        User.objects.create_user(username='existing', password='pass')
        response = self.client.post(reverse('signup'), {
            'username': 'existing',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')

    def test_signup_logs_in_user(self):
        self.client.post(reverse('signup'), {
            'username': 'autouser',
            'password': 'testpass123',
        })
        response = self.client.get(reverse('dashboard'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_authenticated_user_redirects_from_signup(self):
        User.objects.create_user(username='existing', password='pass')
        self.client.login(username='existing', password='pass')
        response = self.client.get(reverse('signup'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_signup_creates_household(self):
        response = self.client.post(reverse('signup'), {
            'username': 'hhuser',
            'password': 'testpass123',
        })
        self.assertRedirects(response, reverse('dashboard'))
        household = Household.objects.get(name="hhuser's Household")
        self.assertIn(User.objects.get(username='hhuser'), household.partners.all())
        self.assertEqual(household.default_interval_days, 3)


class TestLoginLogoutViews(TestCase):
    """Issue #23: Implement login and logout using Django auth views"""

    def setUp(self):
        self.client = Client()
        User.objects.create_user(username='logintest', password='testpass123')

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_login_with_valid_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': 'logintest',
            'password': 'testpass123',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_invalid_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': 'logintest',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "didn't match")

    def test_login_redirects_to_dashboard(self):
        self.client.post(reverse('login'), {
            'username': 'logintest',
            'password': 'testpass123',
        })
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_logged_out_page_loads(self):
        self.client.login(username='logintest', password='testpass123')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

    def test_logout_logs_out_user(self):
        self.client.login(username='logintest', password='testpass123')
        self.client.post(reverse('logout'))
        response = self.client.get(reverse('dashboard'))
        # Should redirect to login since user is not authenticated
        self.assertRedirects(response, reverse('login'))


class TestSignupWithInviteCode(TestCase):
    """Issue #25: Join existing household via invite code"""

    def setUp(self):
        self.client = Client()

    def test_signup_with_valid_invite_code_joins_household(self):
        """Signup with valid invite code creates user and adds to existing household."""
        household = Household.objects.create(name='Existing HH', invite_code='ABCD1234')
        User.objects.create_user(username='partner', password='pass')
        household.partners.add(User.objects.get(username='partner'))

        response = self.client.post(reverse('signup'), {
            'username': 'joinuser',
            'password': 'testpass123',
            'invite_code': 'ABCD1234',
        })
        self.assertRedirects(response, reverse('dashboard'))
        user = User.objects.get(username='joinuser')
        self.assertIn(user, household.partners.all())

    def test_signup_with_invalid_invite_code_shows_error(self):
        response = self.client.post(reverse('signup'), {
            'username': 'badjoin',
            'password': 'testpass123',
            'invite_code': 'INVALID999',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid invite code')

    def test_signup_with_invalid_invite_code_preserves_input(self):
        response = self.client.post(reverse('signup'), {
            'username': 'badjoin2',
            'password': 'testpass123',
            'invite_code': 'INVALID999',
        })
        self.assertContains(response, 'INVALID999')

    def test_signup_with_empty_invite_code_creates_household(self):
        """Empty invite code should create a new household (not try to join)."""
        response = self.client.post(reverse('signup'), {
            'username': 'noinvite',
            'password': 'testpass123',
            'invite_code': '',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(Household.objects.filter(name="noinvite's Household").exists())


class TestHouseholdCreation(TestCase):
    """Issue #24: Household creation and automatic assignment to first user"""

    def setUp(self):
        self.client = Client()

    def test_signup_creates_household_with_user_as_partner(self):
        """New signup creates a Household and adds the user as a partner."""
        self.client.post(reverse('signup'), {
            'username': 'firstuser',
            'password': 'testpass123',
        })
        household = Household.objects.get(name="firstuser's Household")
        user = User.objects.get(username='firstuser')
        self.assertIn(user, household.partners.all())

    def test_signup_sets_default_interval(self):
        """New household has default_interval_days=3."""
        self.client.post(reverse('signup'), {
            'username': 'intervaluser',
            'password': 'testpass123',
        })
        household = Household.objects.get(name="intervaluser's Household")
        self.assertEqual(household.default_interval_days, 3)

    def test_signup_redirects_to_dashboard(self):
        """After signup with household creation, redirect to dashboard."""
        response = self.client.post(reverse('signup'), {
            'username': 'dashuser',
            'password': 'testpass123',
        })
        self.assertRedirects(response, reverse('dashboard'))


class TestInviteCodeGeneration(TestCase):
    """Issue #26: Generate unique invite code for household"""

    def test_generate_invite_code_returns_string(self):
        code = Household.generate_invite_code()
        self.assertIsInstance(code, str)

    def test_generate_invite_code_is_8_chars(self):
        code = Household.generate_invite_code()
        self.assertEqual(len(code), 8)

    def test_generate_invite_code_is_alphanumeric(self):
        code = Household.generate_invite_code()
        self.assertTrue(code.isalnum())

    def test_generate_invite_code_uses_uppercase_and_digits(self):
        # Run multiple times to increase chance of hitting both letters and digits
        codes = {Household.generate_invite_code() for _ in range(50)}
        for code in codes:
            self.assertTrue(all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' for c in code))

    def test_generate_invite_code_unique(self):
        Household.objects.create(name='HH1')
        Household.objects.create(name='HH2')
        # Existing households already have codes from auto-generation
        # Generate new code should not collide
        new_code = Household.generate_invite_code()
        self.assertNotIn(new_code, Household.objects.values_list('invite_code', flat=True))

    def test_household_auto_generates_code_on_save(self):
        household = Household.objects.create(name='Auto HH')
        self.assertTrue(len(household.invite_code) == 8)
        self.assertTrue(household.invite_code.isalnum())

    def test_household_custom_invite_code_preserved(self):
        household = Household.objects.create(name='Custom HH', invite_code='MYCODE12')
        self.assertEqual(household.invite_code, 'MYCODE12')

    def test_household_regenerate_code_in_view(self):
        """POST to household_settings with regenerate_code action changes the code."""
        household = Household.objects.create(name='Regen HH')
        user = User.objects.create_user(username='regenuser', password='pass')
        household.partners.add(user)

        self.client.login(username='regenuser', password='pass')
        old_code = household.invite_code
        response = self.client.post(reverse('household_settings'), {
            'action': 'regenerate_code',
        })
        self.assertRedirects(response, reverse('household_settings'))

        household.refresh_from_db()
        self.assertNotEqual(household.invite_code, old_code)


class TestHouseholdSettingsView(TestCase):
    def test_household_settings_loads(self):
        household = Household.objects.create(name='Settings HH')
        user = User.objects.create_user(username='settingsuser', password='pass')
        household.partners.add(user)
        self.client.login(username='settingsuser', password='pass')
        response = self.client.get(reverse('household_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Settings HH')

    def test_household_settings_shows_invite_code(self):
        household = Household.objects.create(name='Code HH')
        user = User.objects.create_user(username='codeuser', password='pass')
        household.partners.add(user)
        self.client.login(username='codeuser', password='pass')
        response = self.client.get(reverse('household_settings'))
        self.assertContains(response, household.invite_code)


class TestPauseRotationView(TestCase):
    def test_pause_rotation_toggles(self):
        household = Household.objects.create(name='Pause HH')
        user = User.objects.create_user(username='pauseuser', password='pass')
        household.partners.add(user)
        self.client.login(username='pauseuser', password='pass')

        self.assertFalse(household.pause_rotation)
        self.client.post(reverse('pause_rotation'))
        household.refresh_from_db()
        self.assertTrue(household.pause_rotation)

    def test_pause_rotation_redirects(self):
        household = Household.objects.create(name='Pause HH2')
        user = User.objects.create_user(username='pauseuser2', password='pass')
        household.partners.add(user)
        self.client.login(username='pauseuser2', password='pass')
        response = self.client.post(reverse('pause_rotation'))
        self.assertRedirects(response, reverse('household_settings'))

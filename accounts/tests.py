from django.test import TestCase, Client, override_settings
from django.urls import reverse

from .forms import RegisterForm
from .models import CustomUser

# Bypass WhiteNoise manifest requirement during tests
SIMPLE_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'


# ── Helpers ───────────────────────────────────────────────────

def make_user(
    email='test@example.com',
    username='testuser',
    password='StrongPass123!',
    first_name='Test',
    last_name='User',
    role=CustomUser.ROLE_USER,
    is_staff=False,
    is_active=True,
):
    user = CustomUser.objects.create_user(
        email=email, username=username, password=password,
        first_name=first_name, last_name=last_name,
        role=role, is_staff=is_staff,
    )
    user.is_active = is_active
    user.save()
    return user


def make_admin(email='admin@example.com', username='adminuser'):
    return make_user(
        email=email, username=username,
        role=CustomUser.ROLE_ADMIN, is_staff=True,
    )


# ── Model tests ───────────────────────────────────────────────

class CustomUserModelTest(TestCase):

    def test_email_stored_correctly(self):
        user = make_user()
        self.assertEqual(user.email, 'test@example.com')

    def test_is_admin_role_true_for_admin_role(self):
        user = make_user(role=CustomUser.ROLE_ADMIN)
        self.assertTrue(user.is_admin_role)

    def test_is_admin_role_true_for_is_staff(self):
        user = make_user(is_staff=True)
        self.assertTrue(user.is_admin_role)

    def test_is_admin_role_false_for_regular_user(self):
        user = make_user(role=CustomUser.ROLE_USER)
        self.assertFalse(user.is_admin_role)

    def test_str_returns_email(self):
        user = make_user()
        self.assertEqual(str(user), 'test@example.com')

    def test_role_syncs_to_admin_when_is_staff_set(self):
        user = make_user()
        user.is_staff = True
        user.save()
        self.assertEqual(user.role, CustomUser.ROLE_ADMIN)

    def test_default_role_is_user(self):
        user = make_user()
        self.assertEqual(user.role, CustomUser.ROLE_USER)

    def test_inactive_user_created_correctly(self):
        user = make_user(is_active=False)
        self.assertFalse(user.is_active)


# ── RegisterForm tests ────────────────────────────────────────

class RegisterFormTest(TestCase):

    def _valid_data(self, **overrides):
        data = {
            'username': 'janedoe',
            'email': 'jane@example.com',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'password1': 'SecurePass99!',
            'password2': 'SecurePass99!',
        }
        data.update(overrides)
        return data

    def test_valid_form_passes(self):
        form = RegisterForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_username_starting_with_underscore_rejected(self):
        form = RegisterForm(data=self._valid_data(username='_bad'))
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_username_all_underscores_rejected(self):
        form = RegisterForm(data=self._valid_data(username='___'))
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_username_starting_with_digit_rejected(self):
        form = RegisterForm(data=self._valid_data(username='1bad'))
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_username_too_short_rejected(self):
        form = RegisterForm(data=self._valid_data(username='ab'))
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_username_with_spaces_rejected(self):
        form = RegisterForm(data=self._valid_data(username='jane doe'))
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_username_duplicate_case_insensitive_rejected(self):
        make_user(username='janedoe')
        form = RegisterForm(data=self._valid_data(username='JaneDoe'))
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_valid_username_with_underscore_in_middle_accepted(self):
        form = RegisterForm(data=self._valid_data(username='jane_doe'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_email_duplicate_rejected(self):
        make_user(email='jane@example.com')
        form = RegisterForm(data=self._valid_data())
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_email_duplicate_different_case_rejected(self):
        make_user(email='jane@example.com')
        form = RegisterForm(data=self._valid_data(email='JANE@EXAMPLE.COM'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_email_without_at_sign_rejected(self):
        form = RegisterForm(data=self._valid_data(email='notanemail'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_email_without_tld_rejected(self):
        form = RegisterForm(data=self._valid_data(email='jane@nodot'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_password_same_as_email_rejected(self):
        # Django's password validators flag this
        form = RegisterForm(data=self._valid_data(
            email='ab@cd.ef',
            password1='ab@cd.ef',
            password2='ab@cd.ef',
        ))
        self.assertFalse(form.is_valid())

    def test_first_name_too_short_rejected(self):
        form = RegisterForm(data=self._valid_data(first_name='A'))
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)

    def test_first_name_with_digits_rejected(self):
        form = RegisterForm(data=self._valid_data(first_name='Jane2'))
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)

    def test_last_name_too_short_rejected(self):
        form = RegisterForm(data=self._valid_data(last_name='D'))
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', form.errors)

    def test_hyphenated_name_accepted(self):
        form = RegisterForm(data=self._valid_data(first_name='Mary-Jane', last_name='Smith-Jones'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_password_mismatch_rejected(self):
        form = RegisterForm(data=self._valid_data(password2='WrongPass99!'))
        self.assertFalse(form.is_valid())

    def test_all_numeric_password_rejected(self):
        form = RegisterForm(data=self._valid_data(password1='12345678', password2='12345678'))
        self.assertFalse(form.is_valid())


# ── View tests: register ──────────────────────────────────────

@override_settings(STATICFILES_STORAGE=SIMPLE_STORAGE)
class RegisterViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('register')

    def test_get_renders_register_page(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'accounts/register.html')

    def test_successful_registration_redirects_to_post_list(self):
        resp = self.client.post(self.url, {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'SecurePass99!',
            'password2': 'SecurePass99!',
        })
        self.assertRedirects(resp, reverse('post_list'), fetch_redirect_response=False)
        self.assertTrue(CustomUser.objects.filter(email='new@example.com').exists())

    def test_duplicate_email_stays_on_page(self):
        make_user(email='dup@example.com')
        resp = self.client.post(self.url, {
            'username': 'anotheruser',
            'email': 'dup@example.com',
            'first_name': 'Dup',
            'last_name': 'User',
            'password1': 'SecurePass99!',
            'password2': 'SecurePass99!',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(username='anotheruser').exists())

    def test_symbol_only_username_blocked(self):
        resp = self.client.post(self.url, {
            'username': '___',
            'email': 'sym@example.com',
            'first_name': 'Sym',
            'last_name': 'User',
            'password1': 'SecurePass99!',
            'password2': 'SecurePass99!',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(email='sym@example.com').exists())

    def test_authenticated_user_redirected_away_from_register(self):
        user = make_user()
        self.client.force_login(user)
        resp = self.client.get(self.url)
        self.assertRedirects(resp, reverse('post_list'), fetch_redirect_response=False)


# ── View tests: login ─────────────────────────────────────────

@override_settings(STATICFILES_STORAGE=SIMPLE_STORAGE)
class LoginViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('login')
        self.user = make_user()

    def test_get_renders_login_page(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'accounts/login.html')

    def test_correct_credentials_redirect(self):
        resp = self.client.post(self.url, {
            'email': 'test@example.com',
            'password': 'StrongPass123!',
        })
        self.assertRedirects(resp, '/', fetch_redirect_response=False)

    def test_wrong_password_stays_on_page(self):
        resp = self.client.post(self.url, {
            'email': 'test@example.com',
            'password': 'WrongPassword!',
        })
        self.assertEqual(resp.status_code, 200)

    def test_nonexistent_email_stays_on_page(self):
        resp = self.client.post(self.url, {
            'email': 'nobody@example.com',
            'password': 'StrongPass123!',
        })
        self.assertEqual(resp.status_code, 200)

    def test_invalid_email_format_stays_on_page(self):
        resp = self.client.post(self.url, {
            'email': 'notanemail',
            'password': 'StrongPass123!',
        })
        self.assertEqual(resp.status_code, 200)

    def test_empty_fields_rejected(self):
        resp = self.client.post(self.url, {'email': '', 'password': ''})
        self.assertEqual(resp.status_code, 200)

    def test_inactive_user_blocked(self):
        make_user(email='inactive@example.com', username='inactive', is_active=False)
        resp = self.client.post(self.url, {
            'email': 'inactive@example.com',
            'password': 'StrongPass123!',
        })
        self.assertEqual(resp.status_code, 200)

    def test_authenticated_user_redirected_away_from_login(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.url)
        self.assertRedirects(resp, reverse('post_list'), fetch_redirect_response=False)

    def test_next_param_honoured(self):
        resp = self.client.post(self.url + '?next=/about/', {
            'email': 'test@example.com',
            'password': 'StrongPass123!',
        })
        self.assertRedirects(resp, '/about/', fetch_redirect_response=False)

    def test_external_next_param_falls_back_to_root(self):
        resp = self.client.post(self.url + '?next=https://evil.com', {
            'email': 'test@example.com',
            'password': 'StrongPass123!',
        })
        self.assertRedirects(resp, '/', fetch_redirect_response=False)


# ── View tests: logout ────────────────────────────────────────

@override_settings(STATICFILES_STORAGE=SIMPLE_STORAGE)
class LogoutViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)

    def test_post_logout_redirects_to_login(self):
        resp = self.client.post(reverse('logout'))
        self.assertRedirects(resp, reverse('login'), fetch_redirect_response=False)

    def test_user_is_actually_logged_out(self):
        self.client.post(reverse('logout'))
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 302)


# ── View tests: profile ───────────────────────────────────────

@override_settings(STATICFILES_STORAGE=SIMPLE_STORAGE)
class ProfileViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.force_login(self.user)
        self.url = reverse('profile')

    def test_get_renders_profile_page(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'accounts/profile.html')

    def test_unauthenticated_user_redirected_to_login(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp['Location'])

    def test_valid_update_saves_and_redirects(self):
        resp = self.client.post(self.url, {
            'username': 'updateduser',
            'first_name': 'Updated',
            'last_name': 'User',
            'bio': 'Hello world',
        })
        self.assertRedirects(resp, self.url, fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'updateduser')

    def test_symbol_only_username_rejected(self):
        resp = self.client.post(self.url, {
            'username': '___',
            'first_name': 'Test',
            'last_name': 'User',
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.username, '___')


# ── Admin dashboard user views ────────────────────────────────

@override_settings(STATICFILES_STORAGE=SIMPLE_STORAGE)
class DashboardUserViewsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.regular = make_user()
        self.client.force_login(self.admin)

    def test_user_list_accessible_to_admin(self):
        resp = self.client.get(reverse('dashboard_user_list'))
        self.assertEqual(resp.status_code, 200)

    def test_user_list_blocked_for_regular_user(self):
        self.client.force_login(self.regular)
        resp = self.client.get(reverse('dashboard_user_list'))
        # Redirects away — don't follow to avoid rendering post_list template
        self.assertEqual(resp.status_code, 302)

    def test_create_user_get_renders_form(self):
        resp = self.client.get(reverse('dashboard_user_create'))
        self.assertEqual(resp.status_code, 200)

    def test_create_user_post_creates_account(self):
        resp = self.client.post(reverse('dashboard_user_create'), {
            'username': 'brandnew',
            'email': 'brandnew@example.com',
            'first_name': 'Brand',
            'last_name': 'New',
            'role': CustomUser.ROLE_USER,
            'is_active': True,
            'is_staff': False,
            'password': 'SecurePass99!',
        })
        self.assertRedirects(resp, reverse('dashboard_user_list'), fetch_redirect_response=False)
        self.assertTrue(CustomUser.objects.filter(email='brandnew@example.com').exists())

    def test_delete_user_removes_from_db(self):
        victim = make_user(email='victim@example.com', username='victim')
        resp = self.client.post(reverse('dashboard_user_delete', args=[victim.pk]))
        self.assertRedirects(resp, reverse('dashboard_user_list'), fetch_redirect_response=False)
        self.assertFalse(CustomUser.objects.filter(pk=victim.pk).exists())

    def test_admin_cannot_delete_own_account(self):
        resp = self.client.post(reverse('dashboard_user_delete', args=[self.admin.pk]))
        self.assertRedirects(resp, reverse('dashboard_user_list'), fetch_redirect_response=False)
        self.assertTrue(CustomUser.objects.filter(pk=self.admin.pk).exists())

    def test_unauthenticated_user_blocked(self):
        self.client.logout()
        resp = self.client.get(reverse('dashboard_user_list'))
        self.assertEqual(resp.status_code, 302)
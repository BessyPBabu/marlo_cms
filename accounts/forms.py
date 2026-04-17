import re
import logging

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import CustomUser

logger = logging.getLogger(__name__)

# Username: must start with a letter, 3-30 chars, letters/digits/hyphen/underscore only
USERNAME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{2,29}$')

# Name: letters, spaces, hyphens and apostrophes only
NAME_RE = re.compile(r"^[a-zA-Z\s\-']+$")


def _validate_username(username, exclude_pk=None):
    """
    Shared username validation used by every form that accepts a username field.
    Raises ValidationError on failure, returns the cleaned value on success.
    """
    username = username.strip()

    if not username:
        raise forms.ValidationError("Username is required.")

    if not USERNAME_RE.match(username):
        raise forms.ValidationError(
            "Username must start with a letter and be 3–30 characters long. "
            "Only letters, numbers, hyphens (-), and underscores (_) are allowed."
        )

    qs = CustomUser.objects.filter(username__iexact=username)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise forms.ValidationError("That username is already taken.")

    return username


def _validate_name(value, field_label):
    """Shared first/last name validation."""
    value = value.strip()
    if len(value) < 2:
        raise forms.ValidationError(f"{field_label} must be at least 2 characters.")
    if not NAME_RE.match(value):
        raise forms.ValidationError(
            f"{field_label} may only contain letters, spaces, hyphens, and apostrophes."
        )
    return value


def _validate_email(email, exclude_pk=None):
    """Shared email uniqueness validation."""
    email = email.strip().lower()
    parts = email.split('@')
    if len(parts) != 2 or '.' not in parts[1]:
        raise forms.ValidationError("Enter a valid email address (e.g. name@example.com).")
    qs = CustomUser.objects.filter(email__iexact=email)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise forms.ValidationError("An account with this email already exists.")
    return email


# ── Public registration form ──────────────────────────────────

class RegisterForm(UserCreationForm):
    email      = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=True)
    last_name  = forms.CharField(max_length=50, required=True)

    class Meta:
        model  = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def clean_username(self):
        return _validate_username(self.cleaned_data.get('username', ''))

    def clean_email(self):
        return _validate_email(self.cleaned_data.get('email', ''))

    def clean_first_name(self):
        return _validate_name(self.cleaned_data.get('first_name', ''), 'First name')

    def clean_last_name(self):
        return _validate_name(self.cleaned_data.get('last_name', ''), 'Last name')


# ── Profile update form ───────────────────────────────────────

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model  = CustomUser
        fields = ('username', 'first_name', 'last_name', 'bio', 'avatar')
        widgets = {'bio': forms.Textarea(attrs={'rows': 4})}

    def clean_username(self):
        pk = self.instance.pk if self.instance else None
        return _validate_username(self.cleaned_data.get('username', ''), exclude_pk=pk)


# ── Admin user management form ────────────────────────────────

class AdminUserForm(forms.ModelForm):
    """
    Used in the dashboard to create and edit users.
    Applies the exact same username / name / email rules as RegisterForm
    so admins cannot bypass validation by using the dashboard.
    """

    class Meta:
        model  = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')

    # ── Field-level validators ─────────────────────────────────

    def clean_username(self):
        pk = self.instance.pk if self.instance else None
        return _validate_username(self.cleaned_data.get('username', ''), exclude_pk=pk)

    def clean_email(self):
        pk = self.instance.pk if self.instance else None
        return _validate_email(self.cleaned_data.get('email', ''), exclude_pk=pk)

    def clean_first_name(self):
        value = self.cleaned_data.get('first_name', '').strip()
        # First/last name is optional for admin-created accounts
        if value:
            return _validate_name(value, 'First name')
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get('last_name', '').strip()
        if value:
            return _validate_name(value, 'Last name')
        return value

    # ── Cross-field validation ─────────────────────────────────

    def clean(self):
        cleaned = super().clean()
        is_staff = cleaned.get('is_staff')
        role     = cleaned.get('role')
        # Keep role field in sync with is_staff flag
        if is_staff and role != CustomUser.ROLE_ADMIN:
            cleaned['role'] = CustomUser.ROLE_ADMIN
        return cleaned
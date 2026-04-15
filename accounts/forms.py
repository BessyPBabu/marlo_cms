import re
import logging

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import CustomUser

logger = logging.getLogger(__name__)

USERNAME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{2,29}$')
NAME_RE = re.compile(r"^[a-zA-Z\s\-']+$")


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()

        if not USERNAME_RE.match(username):
            raise forms.ValidationError(
                "Username must start with a letter, be 3–30 characters, "
                "and contain only letters, numbers, hyphens, or underscores."
            )

        if CustomUser.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already taken.")

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        # Basic format check beyond EmailField's own validator
        parts = email.split('@')
        if len(parts) != 2 or '.' not in parts[1]:
            raise forms.ValidationError("Enter a valid email address.")

        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")

        return email

    def clean_first_name(self):
        name = self.cleaned_data.get('first_name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError("First name must be at least 2 characters.")
        if not NAME_RE.match(name):
            raise forms.ValidationError(
                "First name may only contain letters, spaces, hyphens, and apostrophes."
            )
        return name

    def clean_last_name(self):
        name = self.cleaned_data.get('last_name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters.")
        if not NAME_RE.match(name):
            raise forms.ValidationError(
                "Last name may only contain letters, spaces, hyphens, and apostrophes."
            )
        return name


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()

        if not USERNAME_RE.match(username):
            raise forms.ValidationError(
                "Username must start with a letter, be 3–30 characters, "
                "and contain only letters, numbers, hyphens, or underscores."
            )

        qs = CustomUser.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("That username is already taken.")

        return username


class AdminUserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = CustomUser.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('role')
        is_staff = cleaned.get('is_staff')
        if is_staff and role != CustomUser.ROLE_ADMIN:
            cleaned['role'] = CustomUser.ROLE_ADMIN
        return cleaned
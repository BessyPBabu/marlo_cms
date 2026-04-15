import logging

from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from rest_framework_simplejwt.tokens import RefreshToken

from .forms import RegisterForm, ProfileUpdateForm, AdminUserForm
from .models import CustomUser

logger = logging.getLogger(__name__)


def _get_jwt_for_user(user):
    try:
        return str(RefreshToken.for_user(user).access_token)
    except Exception:
        logger.exception("Could not generate JWT for user %s", user.pk)
        return ''


def register_view(request):
    if request.user.is_authenticated:
        return redirect('post_list')

    form = RegisterForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            try:
                user = form.save()
                auth.login(request, user)
                logger.info("New user registered: %s (id=%s)", user.email, user.pk)
                messages.success(request, f"Welcome to MARLO, {user.first_name}! Your account is ready.")
                return redirect('post_list')
            except Exception:
                logger.exception("Unexpected error during registration for email: %s",
                                 form.cleaned_data.get('email', 'unknown'))
                messages.error(request, "Registration failed due to a server error. Please try again.")
        else:
            # Surface the first field error as a top-level message
            first_error = next(
                (err for errors in form.errors.values() for err in errors), None
            )
            if first_error:
                messages.error(request, first_error)
            else:
                messages.error(request, "Please fix the errors below.")

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('post_list')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        if not email or not password:
            messages.error(request, "Both email and password are required.")
            return render(request, 'accounts/login.html')

        # Validate email format before touching the DB
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Enter a valid email address.")
            return render(request, 'accounts/login.html')

        user = auth.authenticate(request, username=email, password=password)

        if user is None:
            logger.warning("Failed login attempt for email: %s", email)
            messages.error(request, "Invalid email or password.")
            return render(request, 'accounts/login.html')

        if not user.is_active:
            logger.warning("Inactive account login attempt: %s", email)
            messages.error(request, "Your account has been disabled. Contact support.")
            return render(request, 'accounts/login.html')

        auth.login(request, user)
        logger.info("User logged in: %s (id=%s)", user.email, user.pk)
        messages.success(request, f"Welcome back, {user.first_name or user.username}!")

        next_url = request.GET.get('next', '/')
        # Security: only redirect to relative paths
        if not next_url.startswith('/'):
            next_url = '/'
        return redirect(next_url)

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    if request.method == 'POST':
        logger.info("User logged out: %s", request.user.email)
        auth.logout(request)
        messages.info(request, "You have been logged out.")
    return redirect('login')


@login_required
def profile_view(request):
    form = ProfileUpdateForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user,
    )

    if request.method == 'POST':
        if form.is_valid():
            try:
                form.save()
                logger.info("Profile updated for user %s (id=%s)", request.user.email, request.user.pk)
                messages.success(request, "Profile updated successfully.")
                return redirect('profile')
            except Exception:
                logger.exception("Error saving profile for user %s", request.user.pk)
                messages.error(request, "Could not save your profile. Please try again.")
        else:
            first_error = next(
                (err for errors in form.errors.values() for err in errors), None
            )
            messages.error(request, first_error or "Please fix the errors below.")

    jwt_token = _get_jwt_for_user(request.user)
    return render(request, 'accounts/profile.html', {
        'form': form,
        'jwt_token': jwt_token,
    })


# ── Admin guard decorator ─────────────────────────────────────

def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin_role:
            logger.warning(
                "Non-admin user %s (id=%s) attempted to access admin view: %s",
                request.user.email, request.user.pk, request.path,
            )
            messages.error(request, "Access denied — admin privileges required.")
            return redirect('post_list')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ── Admin dashboard — user management ────────────────────────

@admin_required
def dashboard_home(request):
    from posts.models import Post
    from comments.models import Comment

    try:
        context = {
            'total_users': CustomUser.objects.count(),
            'total_posts': Post.objects.count(),
            'published_posts': Post.objects.filter(status='published').count(),
            'pending_comments': Comment.objects.filter(status='pending').count(),
        }
    except Exception:
        logger.exception("Error loading dashboard stats for user %s", request.user.pk)
        context = {
            'total_users': 0, 'total_posts': 0,
            'published_posts': 0, 'pending_comments': 0,
        }

    context['jwt_token'] = _get_jwt_for_user(request.user)
    return render(request, 'dashboard/index.html', context)


@admin_required
def user_list(request):
    try:
        users = CustomUser.objects.all().order_by('-date_joined')
    except Exception:
        logger.exception("Error fetching user list")
        users = []
        messages.error(request, "Could not load users.")
    return render(request, 'dashboard/user_list.html', {'users': users})


@admin_required
def user_create(request):
    form = AdminUserForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            try:
                user = form.save(commit=False)
                raw_password = request.POST.get('password', '').strip()
                if raw_password:
                    if len(raw_password) < 8:
                        messages.error(request, "Password must be at least 8 characters.")
                        return render(request, 'dashboard/user_form.html', {'form': form, 'action': 'Create'})
                    user.set_password(raw_password)
                else:
                    user.set_unusable_password()
                user.save()
                logger.info("Admin %s created user: %s (id=%s)", request.user.email, user.email, user.pk)
                messages.success(request, f"User {user.email} created successfully.")
                return redirect('dashboard_user_list')
            except Exception:
                logger.exception("Error creating user by admin %s", request.user.pk)
                messages.error(request, "Could not create user. Please try again.")
        else:
            first_error = next(
                (err for errors in form.errors.values() for err in errors), None
            )
            messages.error(request, first_error or "Please fix the errors below.")

    return render(request, 'dashboard/user_form.html', {'form': form, 'action': 'Create'})


@admin_required
def user_edit(request, user_id):
    user = get_object_or_404(CustomUser, pk=user_id)
    form = AdminUserForm(request.POST or None, instance=user)

    if request.method == 'POST':
        if form.is_valid():
            try:
                form.save()
                logger.info("Admin %s updated user: %s (id=%s)", request.user.email, user.email, user_id)
                messages.success(request, f"User {user.email} updated.")
                return redirect('dashboard_user_list')
            except Exception:
                logger.exception("Error updating user %s by admin %s", user_id, request.user.pk)
                messages.error(request, "Could not update user. Please try again.")
        else:
            first_error = next(
                (err for errors in form.errors.values() for err in errors), None
            )
            messages.error(request, first_error or "Please fix the errors below.")

    return render(request, 'dashboard/user_form.html', {
        'form': form,
        'action': 'Edit',
        'target_user': user,
    })


@admin_required
@require_http_methods(["POST"])
def user_delete(request, user_id):
    user = get_object_or_404(CustomUser, pk=user_id)

    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('dashboard_user_list')

    try:
        email = user.email
        user.delete()
        logger.info("Admin %s deleted user: %s", request.user.email, email)
        messages.success(request, f"User {email} deleted.")
    except Exception:
        logger.exception("Error deleting user %s by admin %s", user_id, request.user.pk)
        messages.error(request, "Could not delete user.")

    return redirect('dashboard_user_list')
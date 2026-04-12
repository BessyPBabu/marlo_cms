import logging

from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from rest_framework_simplejwt.tokens import RefreshToken

from .forms import RegisterForm, ProfileUpdateForm, AdminUserForm
from .models import CustomUser

logger = logging.getLogger(__name__)


def _get_jwt_for_user(user):
    try:
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    except Exception:
        logger.exception("Could not generate JWT for user %s", user.email)
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
                messages.success(request, "Account created. Welcome!")
                logger.info("New user registered: %s", user.email)
                return redirect('post_list')
            except Exception:
                logger.exception("Error during user registration")
                messages.error(request, "Registration failed. Please try again.")
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
            messages.error(request, "Email and password are required.")
            return render(request, 'accounts/login.html')

        user = auth.authenticate(request, username=email, password=password)
        if user:
            if not user.is_active:
                messages.error(request, "Your account has been disabled.")
                return render(request, 'accounts/login.html')
            auth.login(request, user)
            logger.info("User logged in: %s", user.email)
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            logger.warning("Failed login attempt for email: %s", email)
            messages.error(request, "Invalid email or password.")

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    logger.info("User logged out: %s", request.user.email)
    auth.logout(request)
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
                messages.success(request, "Profile updated.")
                logger.info("Profile updated for user %s", request.user.email)
                return redirect('profile')
            except Exception:
                logger.exception("Error saving profile for user %s", request.user.email)
                messages.error(request, "Could not save profile.")
        else:
            messages.error(request, "Please fix the errors below.")

    jwt_token = _get_jwt_for_user(request.user)
    return render(request, 'accounts/profile.html', {
        'form': form,
        'jwt_token': jwt_token,
    })


# ──────────────────────────────────────────────────────
# Admin dashboard — user management
# ──────────────────────────────────────────────────────

def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin_role:
            messages.error(request, "Access denied.")
            return redirect('post_list')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


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
        logger.exception("Error loading dashboard stats")
        context = {}

    jwt_token = _get_jwt_for_user(request.user)
    context['jwt_token'] = jwt_token
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
                # Set a usable password via set_unusable so admin must reset it,
                # or set a temp password — here we require the admin to set one
                raw_password = request.POST.get('password', '')
                if raw_password:
                    user.set_password(raw_password)
                else:
                    user.set_unusable_password()
                user.save()
                messages.success(request, f"User {user.email} created.")
                logger.info("Admin created user: %s", user.email)
                return redirect('dashboard_user_list')
            except Exception:
                logger.exception("Error creating user")
                messages.error(request, "Could not create user.")
        else:
            messages.error(request, "Please fix the errors below.")

    return render(request, 'dashboard/user_form.html', {'form': form, 'action': 'Create'})


@admin_required
def user_edit(request, user_id):
    user = get_object_or_404(CustomUser, pk=user_id)
    form = AdminUserForm(request.POST or None, instance=user)

    if request.method == 'POST':
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "User updated.")
                logger.info("Admin updated user: %s", user.email)
                return redirect('dashboard_user_list')
            except Exception:
                logger.exception("Error updating user %s", user_id)
                messages.error(request, "Could not update user.")
        else:
            messages.error(request, "Please fix the errors below.")

    return render(request, 'dashboard/user_form.html', {
        'form': form,
        'action': 'Edit',
        'target_user': user,
    })


@admin_required
@require_http_methods(["POST"])
def user_delete(request, user_id):
    user = get_object_or_404(CustomUser, pk=user_id)
    # Prevent deleting yourself
    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('dashboard_user_list')
    try:
        email = user.email
        user.delete()
        messages.success(request, f"User {email} deleted.")
        logger.info("Admin deleted user: %s", email)
    except Exception:
        logger.exception("Error deleting user %s", user_id)
        messages.error(request, "Could not delete user.")

    return redirect('dashboard_user_list')

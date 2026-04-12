import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from rest_framework_simplejwt.tokens import RefreshToken

from accounts.views import admin_required
from .forms import PostForm, AttachmentForm
from .models import Post, Attachment

logger = logging.getLogger(__name__)


def _get_jwt(user):
    try:
        return str(RefreshToken.for_user(user).access_token)
    except Exception:
        logger.exception("JWT generation failed for user %s", user.pk)
        return ''


# ──────────────────────────────────────────────────────
# Public views
# ──────────────────────────────────────────────────────

def post_list(request):
    try:
        posts = Post.objects.filter(status='published').select_related('author')
    except Exception:
        logger.exception("Error fetching published posts")
        posts = Post.objects.none()

    paginator = Paginator(posts, 9)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)

    jwt_token = _get_jwt(request.user) if request.user.is_authenticated else ''
    return render(request, 'posts/post_list.html', {
        'page_obj': page_obj,
        'jwt_token': jwt_token,
    })


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status='published')

    # Track reads — skip bots and repeated visits in same session
    session_key = f'read_post_{post.pk}'
    if not request.session.get(session_key):
        post.increment_read_count()
        request.session[session_key] = True

    approved_comments = post.comments.filter(status='approved').select_related('user')
    liked = False
    if request.user.is_authenticated:
        liked = post.likes.filter(user=request.user).exists()

    jwt_token = _get_jwt(request.user) if request.user.is_authenticated else ''
    return render(request, 'posts/post_detail.html', {
        'post': post,
        'comments': approved_comments,
        'liked': liked,
        'jwt_token': jwt_token,
    })


def about(request):
    return render(request, 'about.html')


# ──────────────────────────────────────────────────────
# Admin dashboard — post management
# ──────────────────────────────────────────────────────

@admin_required
def dashboard_post_list(request):
    try:
        posts = Post.objects.select_related('author').order_by('-created_at')
    except Exception:
        logger.exception("Error fetching admin post list")
        posts = Post.objects.none()
        messages.error(request, "Could not load posts.")

    paginator = Paginator(posts, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'dashboard/post_list.html', {'page_obj': page_obj})


@admin_required
def dashboard_post_create(request):
    post_form = PostForm(request.POST or None, request.FILES or None)
    attachment_form = AttachmentForm()

    if request.method == 'POST':
        if post_form.is_valid():
            try:
                post = post_form.save(commit=False)
                post.author = request.user
                if post.status == 'published' and not post.published_at:
                    post.published_at = timezone.now()
                post.save()

                # Handle multiple attachments
                for f in request.FILES.getlist('attachments'):
                    Attachment.objects.create(
                        post=post,
                        file=f,
                        file_name=f.name,
                        file_type=f.content_type,
                    )

                messages.success(request, f"Post '{post.title}' created.")
                logger.info("Post created: %s (id=%s)", post.title, post.pk)
                return redirect('dashboard_post_list')
            except Exception:
                logger.exception("Error creating post")
                messages.error(request, "Could not save post.")
        else:
            messages.error(request, "Please fix the errors below.")

    return render(request, 'dashboard/post_form.html', {
        'post_form': post_form,
        'attachment_form': attachment_form,
        'action': 'Create',
    })


@admin_required
def dashboard_post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    post_form = PostForm(request.POST or None, request.FILES or None, instance=post)
    attachment_form = AttachmentForm()

    if request.method == 'POST':
        if post_form.is_valid():
            try:
                updated = post_form.save(commit=False)
                # Set published_at only on first publish
                if updated.status == 'published' and not post.published_at:
                    updated.published_at = timezone.now()
                updated.save()

                for f in request.FILES.getlist('attachments'):
                    Attachment.objects.create(
                        post=updated,
                        file=f,
                        file_name=f.name,
                        file_type=f.content_type,
                    )

                messages.success(request, "Post updated.")
                logger.info("Post updated: %s (id=%s)", post.title, post.pk)
                return redirect('dashboard_post_list')
            except Exception:
                logger.exception("Error updating post %s", post_id)
                messages.error(request, "Could not update post.")
        else:
            messages.error(request, "Please fix the errors below.")

    return render(request, 'dashboard/post_form.html', {
        'post_form': post_form,
        'attachment_form': attachment_form,
        'post': post,
        'action': 'Edit',
    })


@admin_required
@require_http_methods(["POST"])
def dashboard_post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    try:
        title = post.title
        post.delete()
        messages.success(request, f"Post '{title}' deleted.")
        logger.info("Post deleted: %s", title)
    except Exception:
        logger.exception("Error deleting post %s", post_id)
        messages.error(request, "Could not delete post.")
    return redirect('dashboard_post_list')


@admin_required
@require_http_methods(["POST"])
def dashboard_attachment_delete(request, attachment_id):
    attachment = get_object_or_404(Attachment, pk=attachment_id)
    post_id = attachment.post_id
    try:
        attachment.delete()
        messages.success(request, "Attachment deleted.")
    except Exception:
        logger.exception("Error deleting attachment %s", attachment_id)
        messages.error(request, "Could not delete attachment.")
    return redirect('dashboard_post_edit', post_id=post_id)

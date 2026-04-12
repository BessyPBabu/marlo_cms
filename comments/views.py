import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from accounts.views import admin_required
from .models import Comment

logger = logging.getLogger(__name__)


@admin_required
def dashboard_comment_list(request):
    filter_status = request.GET.get('status', 'pending')
    valid = ['pending', 'approved', 'blocked', 'all']
    if filter_status not in valid:
        filter_status = 'pending'

    try:
        qs = Comment.objects.select_related('user', 'post').order_by('-created_at')
        if filter_status != 'all':
            qs = qs.filter(status=filter_status)
    except Exception:
        logger.exception("Error loading comments in dashboard")
        qs = Comment.objects.none()
        messages.error(request, "Could not load comments.")

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    filter_options = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('blocked', 'Blocked'),
        ('all', 'All'),
    ]
    return render(request, 'dashboard/comment_list.html', {
        'page_obj': page_obj,
        'current_status': filter_status,
        'filter_options': filter_options,
    })


@admin_required
@require_http_methods(["POST"])
def dashboard_comment_moderate(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    action = request.POST.get('action', '')

    action_map = {
        'approve': Comment.STATUS_APPROVED,
        'block': Comment.STATUS_BLOCKED,
        'pending': Comment.STATUS_PENDING,
    }

    if action not in action_map:
        messages.error(request, "Invalid action.")
        return redirect('dashboard_comment_list')

    try:
        comment.status = action_map[action]
        comment.save(update_fields=['status', 'updated_at'])
        messages.success(request, f"Comment marked as {comment.status}.")
        logger.info("Comment %s set to %s by admin %s", comment_id, comment.status, request.user.email)
    except Exception:
        logger.exception("Error moderating comment %s", comment_id)
        messages.error(request, "Could not update comment.")

    next_url = request.POST.get('next', 'dashboard_comment_list')
    return redirect(next_url)


@admin_required
@require_http_methods(["POST"])
def dashboard_comment_delete(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    try:
        comment.delete()
        messages.success(request, "Comment deleted.")
        logger.info("Comment %s deleted by admin %s", comment_id, request.user.email)
    except Exception:
        logger.exception("Error deleting comment %s", comment_id)
        messages.error(request, "Could not delete comment.")
    return redirect('dashboard_comment_list')

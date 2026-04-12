from django.contrib import admin
from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'post__title', 'body')
    ordering = ('-created_at',)
    actions = ['approve_comments', 'block_comments']

    @admin.action(description='Approve selected comments')
    def approve_comments(self, request, queryset):
        queryset.update(status='approved')

    @admin.action(description='Block selected comments')
    def block_comments(self, request, queryset):
        queryset.update(status='blocked')

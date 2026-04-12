from django.contrib import admin
from .models import Post, Attachment


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    readonly_fields = ('file_name', 'file_type', 'uploaded_at')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'read_count', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'content', 'author__email')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('-created_at',)
    inlines = [AttachmentInline]
    readonly_fields = ('read_count', 'created_at', 'updated_at')


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'post', 'file_type', 'uploaded_at')
    readonly_fields = ('uploaded_at',)

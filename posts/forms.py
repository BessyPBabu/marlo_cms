import logging

from django import forms
from django.utils.text import slugify

from .models import Post, Attachment

logger = logging.getLogger(__name__)

FORBIDDEN_TITLE_RE_MSG = (
    "Title must contain at least some letters or numbers "
    "(it cannot be only symbols or spaces)."
)


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'content', 'cover_image', 'status')
        widgets = {
            'content': forms.Textarea(attrs={'rows': 15, 'class': 'rich-editor'}),
            'title': forms.TextInput(attrs={'placeholder': 'Post title...'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()

        if len(title) < 5:
            raise forms.ValidationError("Title must be at least 5 characters.")

        if len(title) > 255:
            raise forms.ValidationError("Title cannot exceed 255 characters.")

        # Slugify to check it produces a usable slug — this is what crashes the app
        # when the title is purely symbols like '___' or '---'
        if not slugify(title):
            raise forms.ValidationError(FORBIDDEN_TITLE_RE_MSG)

        return title

    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if len(content) < 10:
            raise forms.ValidationError("Content must be at least 10 characters.")
        return content


class AttachmentForm(forms.ModelForm):
    ALLOWED_TYPES = {
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/zip',
        'text/plain',
    }
    MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

    class Meta:
        model = Attachment
        fields = ('file',)

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f:
            if f.size > self.MAX_SIZE_BYTES:
                raise forms.ValidationError("File size cannot exceed 20 MB.")
            if hasattr(f, 'content_type') and f.content_type not in self.ALLOWED_TYPES:
                raise forms.ValidationError(
                    "Unsupported file type. Allowed: images, PDF, Word, ZIP, plain text."
                )
        return f
import re
import logging

from django import forms
from django.utils.text import slugify

from .models import Post, Attachment

logger = logging.getLogger(__name__)

# A valid title must contain at least one letter or digit so slugify produces something usable
HAS_ALPHANUMERIC_RE = re.compile(r'[a-zA-Z0-9]')


class PostForm(forms.ModelForm):
    class Meta:
        model   = Post
        fields  = ('title', 'content', 'cover_image', 'status')
        widgets = {
            'content': forms.Textarea(attrs={'rows': 15, 'class': 'rich-editor'}),
            'title':   forms.TextInput(attrs={'placeholder': 'Post title...'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()

        if not title:
            raise forms.ValidationError("Title is required.")

        if len(title) < 5:
            raise forms.ValidationError(
                "Title is too short — please use at least 5 characters."
            )

        if len(title) > 255:
            raise forms.ValidationError(
                "Title is too long — maximum 255 characters allowed."
            )

        # Guard: title must contain at least one letter or digit.
        # Pure symbol strings like '___', '---', '!!!', '...' pass Django's
        # CharField but produce an empty slug which crashed the app before this check.
        if not HAS_ALPHANUMERIC_RE.search(title):
            raise forms.ValidationError(
                "Title must contain at least one letter or number — "
                "it cannot be made up of only symbols (e.g. ___, ---, !!!)."
            )

        # Secondary safety: confirm slugify actually produces something
        if not slugify(title):
            raise forms.ValidationError(
                "Title produced an unusable URL slug. Please add some letters or numbers."
            )

        return title

    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()

        if not content:
            raise forms.ValidationError("Content is required.")

        if len(content) < 10:
            raise forms.ValidationError(
                "Content is too short — please write at least 10 characters."
            )

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
        model  = Attachment
        fields = ('file',)

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f:
            if f.size > self.MAX_SIZE_BYTES:
                raise forms.ValidationError(
                    f"File '{f.name}' is too large ({f.size // (1024*1024)} MB). "
                    "Maximum allowed size is 20 MB."
                )
            if hasattr(f, 'content_type') and f.content_type not in self.ALLOWED_TYPES:
                raise forms.ValidationError(
                    f"File type '{f.content_type}' is not allowed. "
                    "Accepted types: images, PDF, Word documents, ZIP archives, plain text."
                )
        return f
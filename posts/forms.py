import logging

from django import forms

from .models import Post, Attachment

logger = logging.getLogger(__name__)


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
        return title


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ('file',)

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f:
            # 20 MB limit
            if f.size > 20 * 1024 * 1024:
                raise forms.ValidationError("File size cannot exceed 20 MB.")
        return f

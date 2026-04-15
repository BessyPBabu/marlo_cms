from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from posts.models import Post
from .models import Comment
from .serializers import CommentSerializer

SIMPLE_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'


# ── Helpers ───────────────────────────────────────────────────

def make_user(email='user@example.com', username='commenter', is_staff=False):
    role = CustomUser.ROLE_ADMIN if is_staff else CustomUser.ROLE_USER
    return CustomUser.objects.create_user(
        email=email, username=username, password='StrongPass123!',
        first_name='Test', last_name='User', role=role, is_staff=is_staff,
    )


def make_post(author, title='Test Post', status='published'):
    return Post.objects.create(
        author=author, title=title,
        content='Enough content for this post to pass validation.',
        status=status,
    )


def make_comment(post, user, body='A decent comment.', status='approved'):
    return Comment.objects.create(post=post, user=user, body=body, status=status)


def get_token(client, email, password='StrongPass123!'):
    resp = client.post(
        reverse('token_obtain_pair'),
        {'email': email, 'password': password},
        content_type='application/json',
    )
    return resp.json().get('access', '')


# ── Model tests ───────────────────────────────────────────────

class CommentModelTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.post = make_post(self.user)

    def test_default_status_is_pending(self):
        comment = Comment.objects.create(post=self.post, user=self.user, body='Hello!')
        self.assertEqual(comment.status, Comment.STATUS_PENDING)

    def test_str_contains_user_email_and_post_title(self):
        comment = make_comment(self.post, self.user, body='Nice post')
        self.assertIn(self.user.email, str(comment))
        self.assertIn(self.post.title, str(comment))

    def test_ordering_newest_first(self):
        # Use explicit timestamps so ordering is deterministic regardless of speed
        now = timezone.now()
        c1 = Comment.objects.create(post=self.post, user=self.user, body='First')
        c2 = Comment.objects.create(post=self.post, user=self.user, body='Second')

        # Force c1 to be older by updating its timestamp directly
        Comment.objects.filter(pk=c1.pk).update(created_at=now)
        Comment.objects.filter(pk=c2.pk).update(created_at=now + timezone.timedelta(seconds=1))

        comments = list(Comment.objects.all())
        # c2 has the later created_at so should be first with -created_at ordering
        self.assertEqual(comments[0].pk, c2.pk)

    def test_cascade_delete_when_post_deleted(self):
        make_comment(self.post, self.user)
        post_pk = self.post.pk
        self.post.delete()
        self.assertEqual(Comment.objects.filter(post_id=post_pk).count(), 0)

    def test_cascade_delete_when_user_deleted(self):
        user2 = make_user(email='gone@example.com', username='gone')
        make_comment(self.post, user2)
        user_pk = user2.pk
        user2.delete()
        self.assertEqual(Comment.objects.filter(user_id=user_pk).count(), 0)

    def test_approved_comment_visible_via_post_comment_count(self):
        make_comment(self.post, self.user, status='approved')
        self.assertEqual(self.post.comment_count, 1)

    def test_pending_comment_not_counted_in_post_comment_count(self):
        make_comment(self.post, self.user, status='pending')
        self.assertEqual(self.post.comment_count, 0)


# ── Serializer tests ──────────────────────────────────────────

class CommentSerializerTest(TestCase):

    def test_valid_body_passes(self):
        serializer = CommentSerializer(data={'body': 'This is a great article!'})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_body_too_short_rejected(self):
        serializer = CommentSerializer(data={'body': 'X'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('body', serializer.errors)

    def test_empty_body_rejected(self):
        serializer = CommentSerializer(data={'body': ''})
        self.assertFalse(serializer.is_valid())

    def test_whitespace_only_body_rejected(self):
        serializer = CommentSerializer(data={'body': '   '})
        self.assertFalse(serializer.is_valid())
        self.assertIn('body', serializer.errors)

    def test_body_exceeding_2000_chars_rejected(self):
        serializer = CommentSerializer(data={'body': 'a' * 2001})
        self.assertFalse(serializer.is_valid())
        self.assertIn('body', serializer.errors)

    def test_body_exactly_2000_chars_accepted(self):
        serializer = CommentSerializer(data={'body': 'a' * 2000})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_body_stripped_of_whitespace(self):
        serializer = CommentSerializer(data={'body': '  Hello world  '})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['body'], 'Hello world')


# ── API: CommentListCreateAPIView ─────────────────────────────

class CommentListCreateAPITest(TestCase):

    def setUp(self):
        self.client = Client()
        self.author = make_user(email='author@example.com', username='author')
        self.commenter = make_user(email='comm@example.com', username='comm')
        self.post = make_post(self.author)

    def _url(self):
        return f'/api/comments/post/{self.post.slug}/'

    def test_get_returns_only_approved_comments(self):
        make_comment(self.post, self.author, body='Visible', status='approved')
        make_comment(self.post, self.author, body='Hidden', status='pending')
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 200)
        bodies = [c['body'] for c in resp.json()]
        self.assertIn('Visible', bodies)
        self.assertNotIn('Hidden', bodies)

    def test_unauthenticated_post_comment_rejected(self):
        resp = self.client.post(
            self._url(), {'body': 'Nice post!'},
            content_type='application/json',
        )
        self.assertIn(resp.status_code, [401, 403])

    def test_authenticated_comment_creates_pending_record(self):
        token = get_token(self.client, 'comm@example.com')
        resp = self.client.post(
            self._url(), {'body': 'Great read!'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 201)
        comment = Comment.objects.get(body='Great read!')
        self.assertEqual(comment.status, Comment.STATUS_PENDING)

    def test_short_body_returns_400(self):
        token = get_token(self.client, 'comm@example.com')
        resp = self.client.post(
            self._url(), {'body': 'X'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('body', resp.json())

    def test_empty_body_returns_400(self):
        token = get_token(self.client, 'comm@example.com')
        resp = self.client.post(
            self._url(), {'body': ''},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 400)

    def test_nonexistent_post_returns_404(self):
        token = get_token(self.client, 'comm@example.com')
        resp = self.client.post(
            '/api/comments/post/does-not-exist/', {'body': 'Hello!'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 404)

    def test_comment_on_draft_post_returns_404(self):
        draft = make_post(self.author, title='Draft Post', status='draft')
        token = get_token(self.client, 'comm@example.com')
        resp = self.client.post(
            f'/api/comments/post/{draft.slug}/', {'body': 'Should fail'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 404)


# ── API: CommentModerateAPIView ───────────────────────────────

class CommentModerateAPITest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_user(email='admin@example.com', username='admin', is_staff=True)
        self.regular = make_user(email='reg@example.com', username='reg')
        self.post = make_post(self.admin)
        self.comment = make_comment(self.post, self.regular, status='pending')

    def _url(self):
        return f'/api/comments/{self.comment.pk}/'

    def test_admin_can_approve_comment(self):
        token = get_token(self.client, 'admin@example.com')
        resp = self.client.patch(
            self._url(), {'status': 'approved'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 200)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, 'approved')

    def test_admin_can_block_comment(self):
        token = get_token(self.client, 'admin@example.com')
        resp = self.client.patch(
            self._url(), {'status': 'blocked'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 200)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, 'blocked')

    def test_regular_user_cannot_moderate(self):
        token = get_token(self.client, 'reg@example.com')
        resp = self.client.patch(
            self._url(), {'status': 'approved'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_cannot_moderate(self):
        resp = self.client.patch(
            self._url(), {'status': 'approved'},
            content_type='application/json',
        )
        self.assertIn(resp.status_code, [401, 403])

    def test_admin_can_delete_comment(self):
        token = get_token(self.client, 'admin@example.com')
        resp = self.client.delete(
            self._url(),
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_moderate_nonexistent_comment_returns_404(self):
        token = get_token(self.client, 'admin@example.com')
        resp = self.client.patch(
            '/api/comments/99999/', {'status': 'approved'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 404)


# ── Dashboard comment views ───────────────────────────────────

@override_settings(STATICFILES_STORAGE=SIMPLE_STORAGE)
class DashboardCommentViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_user(email='admin@example.com', username='admin', is_staff=True)
        self.user = make_user(email='user@example.com', username='user')
        self.post = make_post(self.admin)
        self.comment = make_comment(self.post, self.user, status='pending')
        self.client.force_login(self.admin)

    def test_comment_list_accessible_to_admin(self):
        resp = self.client.get(reverse('dashboard_comment_list'))
        self.assertEqual(resp.status_code, 200)

    def test_comment_list_blocked_for_regular_user(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('dashboard_comment_list'))
        # Blocked — redirects away, don't follow to avoid static file error on post_list
        self.assertEqual(resp.status_code, 302)

    def test_filter_by_pending_status(self):
        resp = self.client.get(reverse('dashboard_comment_list') + '?status=pending')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'A decent comment.')

    def test_filter_by_approved_shows_correct_items(self):
        make_comment(self.post, self.user, body='Approved one', status='approved')
        resp = self.client.get(reverse('dashboard_comment_list') + '?status=approved')
        self.assertContains(resp, 'Approved one')
        self.assertNotContains(resp, 'A decent comment.')

    def test_moderate_approve_changes_status(self):
        resp = self.client.post(
            reverse('dashboard_comment_moderate', args=[self.comment.pk]),
            {'action': 'approve'},
        )
        self.assertRedirects(
            resp, reverse('dashboard_comment_list'), fetch_redirect_response=False
        )
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, 'approved')

    def test_moderate_block_changes_status(self):
        resp = self.client.post(
            reverse('dashboard_comment_moderate', args=[self.comment.pk]),
            {'action': 'block'},
        )
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, 'blocked')

    def test_invalid_action_does_not_change_status(self):
        resp = self.client.post(
            reverse('dashboard_comment_moderate', args=[self.comment.pk]),
            {'action': 'destroy'},
        )
        self.assertRedirects(
            resp, reverse('dashboard_comment_list'), fetch_redirect_response=False
        )
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.status, 'pending')

    def test_delete_comment_removes_from_db(self):
        resp = self.client.post(
            reverse('dashboard_comment_delete', args=[self.comment.pk]),
        )
        self.assertRedirects(
            resp, reverse('dashboard_comment_list'), fetch_redirect_response=False
        )
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_delete_nonexistent_comment_returns_404(self):
        resp = self.client.post(
            reverse('dashboard_comment_delete', args=[99999]),
        )
        self.assertEqual(resp.status_code, 404)
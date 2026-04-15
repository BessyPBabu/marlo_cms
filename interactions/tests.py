from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from posts.models import Post
from .models import Like


# ── Helpers ───────────────────────────────────────────────────

def make_user(email='user@example.com', username='likeuser', is_staff=False):
    role = CustomUser.ROLE_ADMIN if is_staff else CustomUser.ROLE_USER
    return CustomUser.objects.create_user(
        email=email, username=username, password='StrongPass123!',
        first_name='Like', last_name='User', role=role, is_staff=is_staff,
    )


def make_post(author, title='Like Test Post', status='published'):
    return Post.objects.create(
        author=author, title=title,
        content='Enough content to satisfy validation requirements here.',
        status=status,
    )


def get_token(client, email, password='StrongPass123!'):
    resp = client.post(
        reverse('token_obtain_pair'),
        {'email': email, 'password': password},
        content_type='application/json',
    )
    return resp.json().get('access', '')


def like_url(slug):
    return f'/api/interactions/like/{slug}/'


# ── Model tests ───────────────────────────────────────────────

class LikeModelTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.post = make_post(self.user)

    def test_like_created_successfully(self):
        like = Like.objects.create(post=self.post, user=self.user)
        self.assertEqual(like.post, self.post)
        self.assertEqual(like.user, self.user)

    def test_str_contains_user_email_and_post_title(self):
        like = Like.objects.create(post=self.post, user=self.user)
        self.assertIn(self.user.email, str(like))
        self.assertIn(self.post.title, str(like))

    def test_unique_constraint_prevents_double_like(self):
        from django.db import IntegrityError
        Like.objects.create(post=self.post, user=self.user)
        with self.assertRaises(IntegrityError):
            Like.objects.create(post=self.post, user=self.user)

    def test_cascade_delete_when_post_deleted(self):
        Like.objects.create(post=self.post, user=self.user)
        post_pk = self.post.pk
        self.post.delete()
        self.assertEqual(Like.objects.filter(post_id=post_pk).count(), 0)

    def test_cascade_delete_when_user_deleted(self):
        user2 = make_user(email='gone@example.com', username='gone')
        Like.objects.create(post=self.post, user=user2)
        user_pk = user2.pk
        user2.delete()
        self.assertEqual(Like.objects.filter(user_id=user_pk).count(), 0)

    def test_like_count_increments_on_post(self):
        self.assertEqual(self.post.like_count, 0)
        Like.objects.create(post=self.post, user=self.user)
        self.assertEqual(self.post.like_count, 1)

    def test_ordering_newest_first(self):
        # Force deterministic ordering by setting explicit timestamps
        user2 = make_user(email='user2@example.com', username='user2')
        now = timezone.now()

        l1 = Like.objects.create(post=self.post, user=self.user)
        l2 = Like.objects.create(post=self.post, user=user2)

        # Make l1 older so l2 appears first with -created_at
        Like.objects.filter(pk=l1.pk).update(created_at=now)
        Like.objects.filter(pk=l2.pk).update(created_at=now + timezone.timedelta(seconds=1))

        likes = list(Like.objects.all())
        self.assertEqual(likes[0].pk, l2.pk)


# ── API: LikeToggleAPIView ────────────────────────────────────

class LikeToggleAPITest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.author = make_user(email='author@example.com', username='author')
        self.post = make_post(self.author)

    def _token(self, email='user@example.com'):
        return get_token(self.client, email)

    def test_unauthenticated_like_returns_401_or_403(self):
        resp = self.client.post(like_url(self.post.slug), content_type='application/json')
        self.assertIn(resp.status_code, [401, 403])

    def test_first_like_creates_like_record(self):
        token = self._token()
        resp = self.client.post(
            like_url(self.post.slug),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['liked'])
        self.assertEqual(data['like_count'], 1)
        self.assertTrue(Like.objects.filter(post=self.post, user=self.user).exists())

    def test_second_like_removes_like_record(self):
        Like.objects.create(post=self.post, user=self.user)
        token = self._token()
        resp = self.client.post(
            like_url(self.post.slug),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data['liked'])
        self.assertEqual(data['like_count'], 0)
        self.assertFalse(Like.objects.filter(post=self.post, user=self.user).exists())

    def test_like_count_accurate_with_multiple_users(self):
        user2 = make_user(email='user2@example.com', username='user2')
        user3 = make_user(email='user3@example.com', username='user3')
        Like.objects.create(post=self.post, user=user2)
        Like.objects.create(post=self.post, user=user3)

        token = self._token()
        resp = self.client.post(
            like_url(self.post.slug),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.json()['like_count'], 3)

    def test_nonexistent_post_returns_404(self):
        token = self._token()
        resp = self.client.post(
            like_url('no-such-post'),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 404)

    def test_draft_post_returns_404(self):
        draft = make_post(self.author, title='Secret Draft', status='draft')
        token = self._token()
        resp = self.client.post(
            like_url(draft.slug),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 404)

    def test_response_contains_liked_and_like_count_keys(self):
        token = self._token()
        resp = self.client.post(
            like_url(self.post.slug),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        data = resp.json()
        self.assertIn('liked', data)
        self.assertIn('like_count', data)

    def test_get_method_not_allowed(self):
        token = self._token()
        resp = self.client.get(
            like_url(self.post.slug),
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 405)

    def test_toggle_three_times_ends_up_liked(self):
        token = self._token()
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        url = like_url(self.post.slug)

        self.client.post(url, content_type='application/json', **headers)  # like
        self.client.post(url, content_type='application/json', **headers)  # unlike
        resp = self.client.post(url, content_type='application/json', **headers)  # like again

        self.assertTrue(resp.json()['liked'])
        self.assertEqual(resp.json()['like_count'], 1)

    def test_like_reflects_in_post_like_count_property(self):
        token = self._token()
        self.client.post(
            like_url(self.post.slug),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.post.refresh_from_db()
        self.assertEqual(self.post.like_count, 1)

    def test_two_users_can_like_independently(self):
        user2 = make_user(email='user2@example.com', username='user2')
        token1 = self._token()
        token2 = get_token(self.client, 'user2@example.com')

        r1 = self.client.post(
            like_url(self.post.slug), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token1}',
        )
        self.assertTrue(r1.json()['liked'])

        r2 = self.client.post(
            like_url(self.post.slug), content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token2}',
        )
        self.assertTrue(r2.json()['liked'])
        self.assertEqual(r2.json()['like_count'], 2)


# ── Post.like_count property ──────────────────────────────────

class PostLikeCountPropertyTest(TestCase):

    def setUp(self):
        self.author = make_user()
        self.post = make_post(self.author)

    def test_like_count_zero_initially(self):
        self.assertEqual(self.post.like_count, 0)

    def test_like_count_increments_after_like(self):
        user2 = make_user(email='u2@example.com', username='u2')
        Like.objects.create(post=self.post, user=user2)
        self.assertEqual(self.post.like_count, 1)

    def test_like_count_decrements_after_unlike(self):
        like = Like.objects.create(post=self.post, user=self.author)
        self.assertEqual(self.post.like_count, 1)
        like.delete()
        self.assertEqual(self.post.like_count, 0)

    def test_multiple_likes_counted_correctly(self):
        for i in range(5):
            u = make_user(email=f'u{i}@example.com', username=f'user{i}')
            Like.objects.create(post=self.post, user=u)
        self.assertEqual(self.post.like_count, 5)
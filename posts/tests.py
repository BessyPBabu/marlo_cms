from django.test import TestCase, Client, override_settings
from django.urls import reverse

from accounts.models import CustomUser
from .forms import PostForm
from .models import Post, Attachment

SIMPLE_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'


# ── Helpers ───────────────────────────────────────────────────

def make_user(email='author@example.com', username='author', is_staff=False, role=None):
    role = role or (CustomUser.ROLE_ADMIN if is_staff else CustomUser.ROLE_USER)
    return CustomUser.objects.create_user(
        email=email, username=username, password='StrongPass123!',
        first_name='Test', last_name='Author',
        role=role, is_staff=is_staff,
    )


def make_post(author, title='A Valid Post Title', status='published',
              content='Some decent content here that passes validation.'):
    return Post.objects.create(author=author, title=title, content=content, status=status)


# ── Model tests (no template rendering) ──────────────────────

class PostModelTest(TestCase):

    def setUp(self):
        self.author = make_user()

    def test_slug_generated_on_save(self):
        post = make_post(self.author, title='My First Post')
        self.assertEqual(post.slug, 'my-first-post')

    def test_slug_is_unique_with_counter_suffix(self):
        post1 = make_post(self.author, title='Duplicate Title')
        post2 = make_post(self.author, title='Duplicate Title')
        self.assertNotEqual(post1.slug, post2.slug)
        self.assertIn('duplicate-title', post2.slug)

    def test_existing_slug_not_regenerated_on_update(self):
        post = make_post(self.author, title='Original Title')
        original_slug = post.slug
        post.content = 'Updated content body here.'
        post.save()
        self.assertEqual(post.slug, original_slug)

    def test_symbol_only_title_does_not_crash(self):
        # Regression: slugify('___') == '' caused an infinite loop
        post = Post(author=self.author, title='___', content='Some content here.')
        post.save()
        self.assertNotEqual(post.slug, '')
        self.assertIsNotNone(post.pk)

    def test_all_dash_title_does_not_crash(self):
        post = Post(author=self.author, title='---', content='Some content here.')
        post.save()
        self.assertNotEqual(post.slug, '')

    def test_excerpt_truncates_at_200_chars(self):
        long_content = 'a' * 300
        post = make_post(self.author, content=long_content)
        # 200 chars + '...' = 203
        self.assertEqual(len(post.excerpt), 203)
        self.assertTrue(post.excerpt.endswith('...'))

    def test_excerpt_returns_full_content_when_short(self):
        post = make_post(self.author, content='Short content.')
        self.assertEqual(post.excerpt, 'Short content.')

    def test_like_count_starts_at_zero(self):
        post = make_post(self.author)
        self.assertEqual(post.like_count, 0)

    def test_comment_count_only_counts_approved(self):
        from comments.models import Comment
        post = make_post(self.author)
        Comment.objects.create(post=post, user=self.author, body='Approved', status='approved')
        Comment.objects.create(post=post, user=self.author, body='Pending', status='pending')
        Comment.objects.create(post=post, user=self.author, body='Blocked', status='blocked')
        self.assertEqual(post.comment_count, 1)

    def test_increment_read_count_increases_by_one(self):
        post = make_post(self.author)
        self.assertEqual(post.read_count, 0)
        post.increment_read_count()
        post.refresh_from_db()
        self.assertEqual(post.read_count, 1)

    def test_increment_read_count_multiple_times(self):
        post = make_post(self.author)
        post.increment_read_count()
        post.increment_read_count()
        post.increment_read_count()
        post.refresh_from_db()
        self.assertEqual(post.read_count, 3)

    def test_str_returns_title(self):
        post = make_post(self.author, title='My Post')
        self.assertEqual(str(post), 'My Post')

    def test_draft_post_not_visible_in_published_filter(self):
        make_post(self.author, title='Draft', status='draft')
        published = Post.objects.filter(status='published')
        self.assertEqual(published.count(), 0)


# ── PostForm tests ────────────────────────────────────────────

class PostFormTest(TestCase):

    def _valid_data(self, **overrides):
        data = {
            'title': 'A Valid Post Title',
            'content': 'This is valid content with more than ten characters.',
            'status': 'draft',
        }
        data.update(overrides)
        return data

    def test_valid_form_passes(self):
        form = PostForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_title_too_short_rejected(self):
        form = PostForm(data=self._valid_data(title='Hi'))
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_title_only_underscores_rejected(self):
        # This is the crash-fix regression test
        form = PostForm(data=self._valid_data(title='___'))
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_title_only_dashes_rejected(self):
        form = PostForm(data=self._valid_data(title='---'))
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_title_only_spaces_rejected(self):
        form = PostForm(data=self._valid_data(title='     '))
        self.assertFalse(form.is_valid())

    def test_title_too_long_rejected(self):
        form = PostForm(data=self._valid_data(title='A' * 256))
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)

    def test_content_too_short_rejected(self):
        form = PostForm(data=self._valid_data(content='Hi'))
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)

    def test_empty_title_rejected(self):
        form = PostForm(data=self._valid_data(title=''))
        self.assertFalse(form.is_valid())

    def test_empty_content_rejected(self):
        form = PostForm(data=self._valid_data(content=''))
        self.assertFalse(form.is_valid())

    def test_title_with_letters_and_underscores_accepted(self):
        # A title like 'Hello_World' has real letters so slugify works
        form = PostForm(data=self._valid_data(title='Hello_World Post'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_published_status_accepted(self):
        form = PostForm(data=self._valid_data(status='published'))
        self.assertTrue(form.is_valid(), form.errors)


# ── Public view tests ─────────────────────────────────────────

@override_settings(STATICFILES_STORAGE=SIMPLE_STORAGE)
class PostListViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.author = make_user()

    def test_empty_list_renders_200(self):
        resp = self.client.get(reverse('post_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'posts/post_list.html')

    def test_only_published_posts_shown_to_public(self):
        make_post(self.author, title='Published Post', status='published')
        make_post(self.author, title='Draft Post', status='draft')
        resp = self.client.get(reverse('post_list'))
        self.assertContains(resp, 'Published Post')
        self.assertNotContains(resp, 'Draft Post')

    def test_pagination_shows_9_per_page(self):
        for i in range(12):
            make_post(self.author, title=f'Post Number {i:02d}', status='published')
        resp = self.client.get(reverse('post_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['page_obj'].object_list), 9)

    def test_page_2_shows_remaining_posts(self):
        for i in range(12):
            make_post(self.author, title=f'Post Number {i:02d}', status='published')
        resp = self.client.get(reverse('post_list') + '?page=2')
        self.assertEqual(len(resp.context['page_obj'].object_list), 3)


@override_settings(STATICFILES_STORAGE=SIMPLE_STORAGE)
class PostDetailViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.author = make_user()
        self.post = make_post(self.author, title='Detail View Post', status='published')

    def test_published_post_accessible(self):
        resp = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Detail View Post')

    def test_draft_post_returns_404(self):
        draft = make_post(self.author, title='Secret Draft', status='draft')
        resp = self.client.get(reverse('post_detail', args=[draft.slug]))
        self.assertEqual(resp.status_code, 404)

    def test_invalid_slug_returns_404(self):
        resp = self.client.get(reverse('post_detail', args=['does-not-exist']))
        self.assertEqual(resp.status_code, 404)

    def test_read_count_increments_on_first_visit(self):
        initial = self.post.read_count
        self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.post.refresh_from_db()
        self.assertEqual(self.post.read_count, initial + 1)

    def test_read_count_not_incremented_on_second_visit_same_session(self):
        self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.post.refresh_from_db()
        count_after_first = self.post.read_count
        self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.post.refresh_from_db()
        self.assertEqual(self.post.read_count, count_after_first)

    def test_liked_context_is_false_for_unauthenticated(self):
        resp = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertFalse(resp.context['liked'])

    def test_liked_context_true_when_user_has_liked(self):
        from interactions.models import Like
        user = make_user(email='liker@example.com', username='liker')
        Like.objects.create(post=self.post, user=user)
        self.client.force_login(user)
        resp = self.client.get(reverse('post_detail', args=[self.post.slug]))
        self.assertTrue(resp.context['liked'])

    def test_only_approved_comments_in_context(self):
        from comments.models import Comment
        user = make_user(email='commenter@example.com', username='commenter')
        Comment.objects.create(post=self.post, user=user, body='ApprovedBody', status='approved')
        Comment.objects.create(post=self.post, user=user, body='PendingBody', status='pending')
        resp = self.client.get(reverse('post_detail', args=[self.post.slug]))
        bodies = [c.body for c in resp.context['comments']]
        self.assertIn('ApprovedBody', bodies)
        self.assertNotIn('PendingBody', bodies)


# ── Admin dashboard post views ────────────────────────────────

@override_settings(STATICFILES_STORAGE=SIMPLE_STORAGE)
class DashboardPostViewsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_user(email='admin@example.com', username='admin', is_staff=True)
        self.regular = make_user(email='regular@example.com', username='regular')
        self.client.force_login(self.admin)

    def test_post_list_accessible_to_admin(self):
        resp = self.client.get(reverse('dashboard_post_list'))
        self.assertEqual(resp.status_code, 200)

    def test_post_list_blocked_for_regular_user(self):
        self.client.force_login(self.regular)
        resp = self.client.get(reverse('dashboard_post_list'))
        self.assertEqual(resp.status_code, 302)

    def test_create_post_get_renders_form(self):
        resp = self.client.get(reverse('dashboard_post_create'))
        self.assertEqual(resp.status_code, 200)

    def test_create_post_with_valid_data_succeeds(self):
        resp = self.client.post(reverse('dashboard_post_create'), {
            'title': 'Brand New Post',
            'content': 'This content is long enough to pass validation.',
            'status': 'draft',
        })
        self.assertRedirects(resp, reverse('dashboard_post_list'), fetch_redirect_response=False)
        self.assertTrue(Post.objects.filter(title='Brand New Post').exists())

    def test_create_post_with_symbol_title_rejected(self):
        resp = self.client.post(reverse('dashboard_post_create'), {
            'title': '___',
            'content': 'Content here',
            'status': 'draft',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Post.objects.filter(title='___').exists())

    def test_create_post_with_short_title_rejected(self):
        resp = self.client.post(reverse('dashboard_post_create'), {
            'title': 'Hi',
            'content': 'Content here',
            'status': 'draft',
        })
        self.assertEqual(resp.status_code, 200)

    def test_edit_post_get_renders_form(self):
        post = make_post(self.admin, title='Editable Post')
        resp = self.client.get(reverse('dashboard_post_edit', args=[post.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_edit_post_updates_title(self):
        post = make_post(self.admin, title='Old Title Here')
        resp = self.client.post(reverse('dashboard_post_edit', args=[post.pk]), {
            'title': 'Updated Title Here',
            'content': 'Updated content that is long enough.',
            'status': 'published',
        })
        self.assertRedirects(resp, reverse('dashboard_post_list'), fetch_redirect_response=False)
        post.refresh_from_db()
        self.assertEqual(post.title, 'Updated Title Here')

    def test_delete_post_removes_from_db(self):
        post = make_post(self.admin, title='Delete Me Now')
        resp = self.client.post(reverse('dashboard_post_delete', args=[post.pk]))
        self.assertRedirects(resp, reverse('dashboard_post_list'), fetch_redirect_response=False)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_edit_nonexistent_post_returns_404(self):
        resp = self.client.get(reverse('dashboard_post_edit', args=[99999]))
        self.assertEqual(resp.status_code, 404)


# ── REST API tests (no template rendering — no override needed) ─

class PostAPITest(TestCase):

    def setUp(self):
        self.client = Client()
        self.author = make_user()
        self.admin = make_user(email='admin@example.com', username='admin', is_staff=True)
        self.post = make_post(self.author, title='API Post', status='published')

    def _get_token(self, email, password='StrongPass123!'):
        resp = self.client.post(
            reverse('token_obtain_pair'),
            {'email': email, 'password': password},
            content_type='application/json',
        )
        return resp.json().get('access', '')

    def test_list_posts_returns_200_unauthenticated(self):
        resp = self.client.get('/api/posts/')
        self.assertEqual(resp.status_code, 200)

    def test_detail_post_returns_200_unauthenticated(self):
        resp = self.client.get(f'/api/posts/{self.post.slug}/')
        self.assertEqual(resp.status_code, 200)

    def test_detail_returns_correct_slug(self):
        resp = self.client.get(f'/api/posts/{self.post.slug}/')
        self.assertEqual(resp.json()['slug'], self.post.slug)

    def test_create_post_as_regular_user_returns_403(self):
        token = self._get_token('author@example.com')
        resp = self.client.post(
            '/api/posts/create/',
            {'title': 'New Via API', 'content': 'Content here.', 'status': 'draft'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 403)

    def test_create_post_as_admin_returns_201(self):
        token = self._get_token('admin@example.com')
        resp = self.client.post(
            '/api/posts/create/',
            {'title': 'Admin API Post', 'content': 'Long enough content here.', 'status': 'draft'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(Post.objects.filter(title='Admin API Post').exists())

    def test_draft_posts_excluded_from_api_list_for_public(self):
        make_post(self.author, title='Hidden Draft', status='draft')
        resp = self.client.get('/api/posts/')
        titles = [p['title'] for p in resp.json()['results']]
        self.assertNotIn('Hidden Draft', titles)

    def test_unauthenticated_create_returns_401_or_403(self):
        resp = self.client.post(
            '/api/posts/create/',
            {'title': 'No Auth Post', 'content': 'Content.', 'status': 'draft'},
            content_type='application/json',
        )
        self.assertIn(resp.status_code, [401, 403])
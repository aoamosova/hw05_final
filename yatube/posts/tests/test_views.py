import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_follow = User.objects.create_user(username='follow')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='first_test-slug',
            description='Тестовое описание',
        )
        cls.other_group = Group.objects.create(
            title='Тестовая группа 2',
            slug='second_test-slug',
            description='Тестовое описание',
        )
        small_gif = (
             b'\x47\x49\x46\x38\x39\x61\x02\x00'
             b'\x01\x00\x80\x00\x00\x00\x00\x00'
             b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
             b'\x00\x00\x00\x2C\x00\x00\x00\x00'
             b'\x02\x00\x01\x00\x00\x02\x02\x0C'
             b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        for i in range(13):
            cls.posts = Post.objects.create(
                text='Тестовый пост' + str(i),
                author=cls.user,
                group=cls.group,
                image=uploaded,
            )
        cls.post_with_group = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.other_group,
        )
        cls.urls = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}),
            reverse('posts:profile', kwargs={'username': cls.user.username}),
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.posts.author)
        self.authorized_follow = Client()
        self.authorized_follow.force_login(self.user_follow)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.posts.author}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.posts.id}):
            'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.posts.id}):
            'posts/create_post.html',
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """В шаблон страницы index передан правильный контекст"""
        response = self.authorized_client.get(reverse('posts:index'))
        context = response.context['posts'][0]
        model = self.user.posts.all()[0]
        self.assertEqual(context, model)

    def test_group_list_page_show_correct_context(self):
        """В шаблон страницы group_list передан правильный контекст"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        context = response.context['posts'][0]
        model = self.group.posts.all()[0]
        self.assertEqual(context, model)

    def test_profile_page_show_correct_context(self):
        """В шаблон страницы profile передан правильный контекст"""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.posts.author}))
        context = response.context['posts'][0]
        model = self.user.posts.all()[0]
        self.assertEqual(context, model)

    def test_post_detail_page_show_correct_context(self):
        """В шаблон страницы post_detail передан правильный контекст"""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.posts.id}))
        context = response.context['post']
        model = self.posts
        self.assertEqual(context, model)

    def test_post_create_page_show_correct_context(self):
        """В шаблон страницы post_create передан правильный контекст"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """В шаблон страницы post_edit передан правильный контекст"""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.posts.id}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_first_page_contains_ten_records(self):
        """Паджинатор работает правильно на странице 1"""
        for address in PostsPagesTests.urls:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        """Паджинатор работает правильно на странице 2"""
        for address in PostsPagesTests.urls:
            with self.subTest(address=address):
                response = self.authorized_client.get(address + '?page=2')
                self.assertGreaterEqual(
                    len(response.context['page_obj']), 3, 4)

    def test_post_show_on_pages(self):
        """Новый пост появляется на страницах"""
        for address in PostsPagesTests.urls:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTrue(
                    self.posts in response.context['page_obj'].object_list)

    def test_post_not_in_else_group(self):
        """Новый пост не попал в группу, для которой не был предназначен"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertNotIn(self.post_with_group, response.context['posts'])

    def test_auth_user_can_follow(self):
        """Auth пользователь может подписываться на других пользователей
           и удалять их из подписок.
        """
        self.authorized_follow.get(
            reverse('posts:profile_follow', kwargs={'username': self.user}))
        self.assertEqual(Follow.objects.all().count(), 1)
        self.authorized_follow.get(
            reverse('posts:profile_unfollow', kwargs={'username': self.user}))
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_new_post_in_post_list_follow_unfollow(self):
        """Новая запись пользователя появляется в ленте тех,
           кто на него подписан и не появляется в ленте тех, кто не подписан
        """
        self.authorized_follow.get(
            reverse('posts:profile_follow', kwargs={'username': self.user}))
        post = Post.objects.create(author=self.user)
        response = self.authorized_follow.get(reverse('posts:follow_index'))
        context = response.context['page_obj']
        self.assertIn(post, context)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        context = response.context['page_obj']
        self.assertNotIn(post, context)

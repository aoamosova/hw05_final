from http import HTTPStatus

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='the_group',
        )
        cls.post = Post.objects.create(
            author=User.objects.create_user(username='second_test_name'),
            text='Тестовый пост',
        )
        cls.urls = [
            f'/profile/{cls.post.author.username}/',
            f'/group/{cls.group.slug}/',
            '/',
            f'/posts/{cls.post.id}/',
        ]

    def setUp(self):
        self.guest_client = Client()
        self.first_user = User.objects.create_user(username='first_test_name')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.first_user)
        self.second_user = self.post.author
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.second_user)

    def test_pages_urls_for_guest_users(self):
        """Тест доступности страниц guest пользователям."""
        for address in PostsURLTests.urls:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_pages_urls_for_auth_users(self):
        """Тест доступности страниц auth пользователям."""
        for address in PostsURLTests.urls:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_for_auth_users(self):
        """Тест доступности create auth пользователям."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page_for_auth_users(self):
        """Тест доступности unexisting_page auth пользователям."""
        response = self.authorized_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_unexisting_page_for_guest_users(self):
        """Тест доступности unexisting_page guest пользователям."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_edit(self):
        """Тест доступности редактирования Автору поста."""
        response = self.authorized_client_author.get(
            f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_redirect_anonymous_on_auth_login(self):
        """Страница по адресу /create/ перенаправит анонимного
        пользователя на страницу логина.
        """
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_edit_url_redirect_anonymous_on_posts_login(self):
        """Страница по адресу /posts/post_id//edit/ перенаправит анонимного
        пользователя на страницу поста.
        """
        response = self.guest_client.get(
            f'/posts/{self.post.id}/edit/', follow=True)
        self.assertRedirects(response, (f'/posts/{self.post.id}/'))

    def test_edit_url_redirect_auth_not_author_on_posts_login(self):
        """Страница по адресу /posts/post_id/edit/ перенаправит
        не автора поста на страницу поста.
        """
        response = self.authorized_client.get(
            f'/posts/{self.post.id}/edit/', follow=True)
        self.assertRedirects(response, (f'/posts/{self.post.id}/'))

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.second_user}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client_author.get(address)
                self.assertTemplateUsed(response, template)

    def test_commenting_to_guest_not_avaliable(self):
        """Комментарии не доступны гостям сайта."""
        response = self.guest_client.get('/posts/1/comment/', follow=True)
        self.assertRedirects(
            response, (reverse('users:login') + '?next=/posts/1/comment/'))

    def test_cashe(self):
        """Проверяем работу кэша."""
        post = Post.objects.create(
            author=self.post. author, text='Тестовый пост',)
        first_response = self.authorized_client_author.get(
            reverse('posts:index'))
        post_exits = first_response.content
        post.delete()
        second_response = self.authorized_client_author.get(
            reverse('posts:index'))
        post_delete = second_response.content
        self.assertEqual(post_exits, post_delete)
        cache.clear()
        third_response = self.authorized_client_author.get(
            reverse('posts:index'))
        cache_cleared = third_response.content
        self.assertNotEqual(post_exits, cache_cleared)

    def test_page_404_uses_correct_template(self):
        """Cтраница 404 отдает кастомный шаблон."""
        response = self.client.get('/unexisting_page/')
        self.assertTemplateUsed(response, 'core/404.html')

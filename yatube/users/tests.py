from http import HTTPStatus

from django.test import Client, TestCase


class StaticURLTests(TestCase):

    def setUp(self):
        self.guest_client = Client()

    def test_pages(self):
        """Тест доступности страниц пользователям"""
        urls = [
            '/auth/signup/',
            '/auth/login/',
            '/auth/logout/',
        ]
        for address in urls:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/auth/signup/': 'users/signup.html',
            '/auth/login/': 'users/login.html',
            '/auth/logout/': 'users/logged_out.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertTemplateUsed(response, template)

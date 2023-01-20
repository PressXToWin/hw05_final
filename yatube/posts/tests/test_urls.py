from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    def setUp(self):
        # Устанавливаем данные для тестирования
        # Создаём экземпляр клиента. Он неавторизован.
        self.guest_client = Client()

    def test_homepage(self):
        # Отправляем запрос через client,
        # созданный в setUp()
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='testslug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.user = User.objects.get(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Шаблоны по адресам
        templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': f'/group/{self.group.slug}/',
            'posts/profile.html': '/profile/auth/',
            'posts/post_detail.html': f'/posts/{self.post.id}/',
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_404(self):
        """Страница 404 доступна любому пользователю."""
        response = self.guest_client.get('/unexistent-page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_create_url_uses_correct_template(self):
        """Страница по адресу /create/ использует шаблон
        posts/create_post.html."""
        response = self.authorized_client.get('/create/')
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_create_url_guest_client(self):
        """Страница по адресу /create/ редиректит неавторизованного."""
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_edit_url_uses_correct_template(self):
        """Страница по адресу /posts/<id>/edit/ использует шаблон
        posts/create_post.html."""
        response = self.authorized_client.get(f'/posts/{self.post.id}/edit/')
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_edit_url_guest_client(self):
        """Страница по адресу /posts/<id>/edit/ редиректит
        неавторизованного."""
        response = self.guest_client.get(f'/posts/{self.post.id}/edit/',
                                         follow=True)
        self.assertRedirects(response,
                             f'/auth/login/?next=/posts/{self.post.id}/edit/')

    def test_edit_url_wrong_client(self):
        """Страница по адресу /posts/<id>/edit/ редиректит не автора."""
        newuser = User.objects.create_user(username='nonauthor')
        wrong_client = Client()
        wrong_client.force_login(newuser)
        response = wrong_client.get(f'/posts/{self.post.id}/edit/',
                                    follow=True)
        self.assertRedirects(response, f'/posts/{self.post.id}/')

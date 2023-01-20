import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='testslug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Текст',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.user = User.objects.get(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "страница: имя_html_шаблона"
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            (
                reverse('posts:group_list', kwargs={'slug': self.group.slug})
            ): 'posts/group_list.html',
            (
                reverse('posts:profile',
                        kwargs={'username': self.user.username})
            ): 'posts/profile.html',
            (
                reverse('posts:post_detail', kwargs={'post_id': self.post.id})
            ): 'posts/post_detail.html',
            (
                reverse('posts:post_edit', kwargs={'post_id': self.post.id})
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            '/unexistent-page/': 'core/404.html',

        }
        # Проверяем, что при обращении к name вызывается соответствующий
        # HTML-шаблон
        for page_name, template in templates_pages_names.items():
            with self.subTest(page_name=page_name):
                response = self.authorized_client.get(page_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        # Взяли первый элемент из списка и проверили, что его содержание
        # совпадает с ожидаемым
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_author_0 = first_object.author
        post_group_0 = first_object.group
        self.assertEqual(post_text_0, 'Текст')
        self.assertEqual(post_author_0, User.objects.get(username='auth'))
        self.assertEqual(post_group_0, Group.objects.get(slug='testslug'))

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.
                    get(reverse('posts:post_detail',
                                kwargs={'post_id': self.post.id})))
        self.assertEqual(response.context.get('post').text, 'Текст')
        self.assertEqual(response.context.get('post').author, User.objects.get(
            username='auth'))
        self.assertEqual(response.context.get('post').group, Group.objects.get(
            slug='testslug'))

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        # Словарь ожидаемых типов полей формы:
        # указываем, объектами какого класса должны быть поля формы
        form_fields = {
            # При создании формы поля модели типа TextField
            # преобразуются в CharField с виджетом forms.Textarea
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        # Проверяем, что типы полей формы в словаре context
        # соответствуют ожиданиям
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}))
        # Словарь ожидаемых типов полей формы:
        # указываем, объектами какого класса должны быть поля формы
        form_fields = {
            # При создании формы поля модели типа TextField
            # преобразуются в CharField с виджетом forms.Textarea
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        # Проверяем, что типы полей формы в словаре context соответствуют
        # ожиданиям
        postid = response.context.get('post_id')
        isedit = response.context.get('is_edit')
        self.assertEqual(postid, self.post.id)
        self.assertTrue(isedit)
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)

    def test_paginator(self):
        """Проверка: количество постов на первой странице равно 10,
        на второй 3."""
        posts = [Post(text=f'Текст {i}.', author=self.user,
                      group=self.group) for i in range(12)]
        Post.objects.bulk_create(posts)
        reverses = [
            reverse('posts:index'),
            (
                reverse('posts:group_list', kwargs={'slug': 'testslug'})
            ),
            (
                reverse('posts:profile', kwargs={'username': 'auth'})
            ),
        ]
        # Ключ - номер страницы, значение - ожидаемое количество постов
        pages = {'1': 10, '2': 3}
        for page, result in pages.items():
            for reverse_name in reverses:
                with self.subTest(reverse_name=reverse_name):
                    response = self.authorized_client.get(reverse_name,
                                                          {'page': page})
                    self.assertEqual(len(response.context['page_obj']), result)

    def test_post_image_in_context(self):
        """При выводе поста с картинкой изображение передаётся в context."""
        reverses = [
            reverse('posts:index'),
            (
                reverse('posts:profile', kwargs={
                    'username': self.user.username})),
            (
                reverse('posts:group_list', kwargs={'slug': self.group.slug})
            ),
        ]
        for reverse_name in reverses:
            response = self.authorized_client.get(reverse_name)
            # Взяли первый элемент из списка и проверили, что его содержание
            # совпадает с ожидаемым
            first_object = response.context['page_obj'][0]
            post_image_0 = first_object.image
            self.assertEqual(post_image_0, self.post.image)
        # Отдельная проверка для страницы с постом.
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        post_image_0 = response.context['post'].image
        self.assertEqual(post_image_0, self.post.image)

    def test_cache_index(self):
        """Проверяем работу кэша."""
        cache_post = Post.objects.create(
            text='Проверка кэша',
            author=self.user,
        )
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertContains(response, 'Проверка кэша')
        cache_post.delete()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertContains(response, 'Проверка кэша')
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotContains(response, 'Проверка кэша')


class PostsFilteredPagesTests(TestCase):
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
            text='Текст',
            author=cls.user,
            group=cls.group
        )
        # Создадим пост, который не должен появиться
        # в отфильтрованных результатах
        cls.wrong_user = User.objects.create_user(username='wrong')
        cls.wrong_group = Group.objects.create(
            title='Не та группа',
            slug='wrongslug',
            description='Описание',
        )
        cls.wrong_post = Post.objects.create(
            text='Не тот текст',
            author=cls.wrong_user,
            group=cls.wrong_group
        )

    def setUp(self):
        self.user = User.objects.get(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.reverses = [
            (
                reverse('posts:group_list',
                        kwargs={'slug': self.group.slug})
            ),
            (
                reverse('posts:profile',
                        kwargs={'username': self.user.username})
            ),
        ]

    def test_filtered_pages_show_correct_context(self):
        """Шаблоны с отфильтрованными постами сформированы
        с правильным контекстом."""
        for reverse_name in self.reverses:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                # Взяли первый элемент из списка и проверили, что его
                # содержание совпадает с ожидаемым
                first_object = response.context['page_obj'][0]
                post_text_0 = first_object.text
                post_author_0 = first_object.author
                post_group_0 = first_object.group
                self.assertEqual(post_text_0, 'Текст')
                self.assertEqual(post_author_0, User.objects.get(
                    username='auth'))
                self.assertEqual(post_group_0, Group.objects.get(
                    slug='testslug'))

    def test_post_appears(self):
        """Дополнительная проверка при создании поста.
        Убеждаемся, что пост появляется только в нужных местах."""
        for reverse_name in self.reverses:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                page = response.context['page_obj']
                self.assertIn(self.post, page)
        # И убеждаемся что пост не появляется там, где не надо
        response = self.authorized_client.get((
            reverse('posts:group_list',
                    kwargs={'slug': self.wrong_group.slug})))
        page = response.context['page_obj']
        self.assertNotIn(self.post, page)


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.followed_user = User.objects.create_user(username='followed')
        cls.not_following_user = User.objects.create_user(
            username='not_following')
        cls.post = Post.objects.create(
            text='Подписка',
            author=cls.followed_user
        )

    def setUp(self):
        self.user = User.objects.get(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_follow(self):
        """Проверка подписки и отписки"""
        # Запрашиваем подписку
        self.authorized_client.get(reverse('posts:profile_follow', kwargs={
            'username': self.followed_user.username}))
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.followed_user.username}))
        # В контекст страницы профиля передаётся переменная following,
        # если юзер подписан на автора
        self.assertTrue(response.context['following'])
        # Запрашиваем отписку
        self.authorized_client.get(reverse('posts:profile_unfollow', kwargs={
            'username': self.followed_user.username}))
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.followed_user.username}))
        self.assertFalse(response.context['following'])

    def test_post_appearing(self):
        """Дополнительная проверка при создании поста.
        Убеждаемся, что пост появляется только в нужных местах."""
        # Запрашиваем подписку
        self.authorized_client.get(reverse('posts:profile_follow', kwargs={
            'username': self.followed_user.username}))
        # Убеждаемся что пост появляется там, где не надо
        response = self.authorized_client.get(reverse('posts:follow_index'))
        page = response.context['page_obj']
        self.assertIn(self.post, page)
        # И убеждаемся что пост не появляется там, где не надо
        not_following_client = Client()
        not_following_client.force_login(self.not_following_user)
        response = not_following_client.get(reverse('posts:follow_index'))
        page = response.context['page_obj']
        self.assertNotIn(self.post, page)

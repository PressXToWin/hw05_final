import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.get(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.guest_client = Client()

    def test_create_post(self):
        """Валидная форма создает пост."""
        # Подсчитаем количество постов
        post_count = Post.objects.count()
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
        form_data = {
            'text': 'Тестовый текст',
            'group': '',
            'image': uploaded
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse('posts:profile', kwargs={
            'username': 'auth'}))
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), post_count + 1)
        # Проверяем, что создался пост с заданным текстом
        self.assertTrue(Post.objects.filter(
            text='Тестовый текст', image='posts/small.gif').exists())

    def test_guest_try_create_post(self):
        """Проверяем, что гость не может создать пост."""
        # Подсчитаем количество постов
        post_count = Post.objects.count()
        form_data = {
            'text': 'Гостевой текст',
            'group': '',
        }
        # Отправляем POST-запрос
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, '/auth/login/?next=/create/')
        # Проверяем, не увеличилось ли число постов
        self.assertEqual(Post.objects.count(), post_count)
        # Проверяем, что не создался пост с заданным текстом
        self.assertFalse(Post.objects.filter(text='Гостевой текст').exists())

    def test_edit_post(self):
        """Валидная форма редактирует пост."""
        # Создадим пост, который будем редактировать
        post = Post.objects.create(
            text='Неотредактированный текст',
            author=self.user
        )
        # Подсчитаем количество постов
        post_count = Post.objects.count()
        form_data = {
            'text': 'Отредактированный текст',
            'group': '',
        }
        post_id = post.pk
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post_id}),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={
            'post_id': post_id}))
        # Проверяем, не увеличилось ли число постов
        self.assertEqual(Post.objects.count(), post_count)
        # Проверяем, что текст отредактировался
        self.assertEqual(Post.objects.get(pk=post_id).text,
                         'Отредактированный текст')

    def test_guest_try_edit_post(self):
        """Проверяем, что гость не может редактировать пост."""
        # Создадим пост, который будем редактировать
        post = Post.objects.create(
            text='Неотредактированный текст 2',
            author=self.user
        )
        # Подсчитаем количество постов
        post_count = Post.objects.count()
        form_data = {
            'text': 'Отредактированный текст 2',
            'group': '',
        }
        post_id = post.pk
        # Отправляем POST-запрос
        response = self.guest_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post_id}),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response,
                             f'/auth/login/?next=/posts/{post_id}/edit/')
        # Проверяем, не увеличилось ли число постов
        self.assertEqual(Post.objects.count(), post_count)
        # Проверяем, что текст не отредактировался
        self.assertEqual(Post.objects.get(pk=post_id).text,
                         'Неотредактированный текст 2')

    def test_create_comment(self):
        """Проверяем создание комментов."""
        # Подсчитаем количество комментов
        comment_count = Comment.objects.count()
        post = Post.objects.create(
            text='Пост для коммента',
            author=self.user
        )
        form_data = {
            'text': 'Коммент321'
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        # Проверяем, что число комментов увеличилось
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        # Убеждаемся, что текст коммента совпадает
        comment = response.context['comments'][0]
        self.assertEqual(comment.text, 'Коммент321')

    def test_guest_try_create_comment(self):
        """Проверяем, что гость не может создать коммент."""
        # Подсчитаем количество постов
        comment_count = Comment.objects.count()
        post = Post.objects.create(
            text='Пост для коммента',
            author=self.user
        )
        form_data = {
            'text': 'Гостевой коммент'
        }
        # Отправляем POST-запрос
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        # Проверяем, не увеличилось ли число комментов
        self.assertEqual(Comment.objects.count(), comment_count)
        # Проверяем, что не существует коммент с заданным текстом
        self.assertFalse(Comment.objects.filter(
            text='Гостевой коммент').exists())

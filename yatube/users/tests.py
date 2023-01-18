from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .forms import CreationForm

User = get_user_model()


class UserCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = CreationForm()

    def setUp(self):
        self.guest_client = Client()

    def test_create_post(self):
        """Валидная форма создает пользователя."""
        form_data = {
            'first_name': 'Тест',
            'last_name': 'Тестов',
            'username': 'test',
            'email': 'noreply@example.com',
            'password1': 'blahblahblah666',
            'password2': 'blahblahblah666',
        }
        # Отправляем POST-запрос
        self.guest_client.post(
            reverse('users:signup'),
            data=form_data
        )
        # Убеждаемся, что у пользователя с отправленным юзернеймом
        # та же самая почта
        newuser = User.objects.get(username='test')
        self.assertEqual(newuser.email, 'noreply@example.com')

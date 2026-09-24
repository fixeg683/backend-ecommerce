from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from .models import Category, Product, EmailVerification
from .serializers import ProductSerializer


class EmailVerificationCodeFlowTests(TestCase):
    def test_registration_and_verification_use_six_digit_code(self):
        response = self.client.post(
            '/api/register/',
            {'username': 'alice', 'email': 'alice@example.com', 'password': 'strongpass123'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)

        user = get_user_model().objects.get(email='alice@example.com')
        self.assertFalse(user.is_active)

        verification = EmailVerification.objects.get(user=user)
        self.assertIsNotNone(verification.code)
        self.assertEqual(len(verification.code), 6)
        self.assertGreater(verification.expires_at, timezone.now())

        verify_response = self.client.post(
            '/api/verify-code/',
            {'email': user.email, 'code': verification.code},
            format='json',
        )

        self.assertEqual(verify_response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertFalse(EmailVerification.objects.filter(user=user).exists())


class ProductSerializerImageTests(SimpleTestCase):
    def test_image_field_returns_absolute_url_for_relative_image(self):
        request = APIRequestFactory().get('/api/products/')
        category = Category(name='Software')
        product = Product(name='Test Product', description='A test product', price='19.99')
        product.category = category
        product.image = type('ImageStub', (), {'url': '/media/products/test.jpg'})()
        product.file = None
        product.download_url_override = None

        serializer = ProductSerializer(product, context={'request': request})

        expected = 'http://testserver/media/products/test.jpg'
        self.assertEqual(serializer.data['image'], expected)
        self.assertEqual(serializer.data['img'], expected)
        self.assertEqual(serializer.data['image_url'], expected)
        self.assertEqual(serializer.data['imageUrl'], expected)

    def test_download_url_returns_none_when_download_property_raises(self):
        class ExplodingProduct:
            name = 'Broken Product'
            description = 'A test product'
            price = '19.99'
            product_type = 'software'
            is_ebook = False
            image = None
            file = None
            download_url_override = None
            category = Category(name='Software')

            @property
            def downloadable_file(self):
                raise RuntimeError('Cloudinary config is broken')

        serializer = ProductSerializer(ExplodingProduct(), context={})

        self.assertIsNone(serializer.data['download_url'])

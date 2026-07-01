from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from .models import Category, Product
from .serializers import ProductSerializer


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

        self.assertEqual(
            serializer.data['image'],
            'http://testserver/media/products/test.jpg',
        )

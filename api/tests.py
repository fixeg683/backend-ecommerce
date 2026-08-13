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

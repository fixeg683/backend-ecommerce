from rest_framework import serializers
from .models import Product, Order

class ProductSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'image', 
                  'image_url', 'file', 'stock', 'category', 'created_at']

    def get_image_url(self, obj):
        if obj.image:
            # Cloudinary URLs are already absolute — return as-is
            url = str(obj.image.url)
            if url.startswith('http'):
                return url
            # Fallback for local dev
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
        return None
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Product, Category, Order, OrderItem


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ['id', 'name']


class ProductSerializer(serializers.ModelSerializer):
    category_name    = serializers.CharField(source='category.name', read_only=True)
    image            = serializers.SerializerMethodField()
    img              = serializers.SerializerMethodField()
    image_url        = serializers.SerializerMethodField()
    imageUrl         = serializers.SerializerMethodField()
    download_url     = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'description', 'price',
            'product_type', 'is_ebook',
            'image', 'img', 'image_url', 'imageUrl',
            'file', 'download_url',
            'stock', 'category', 'category_name',
            'created_at',
        ]

    def _get_image_url(self, obj):
        image = getattr(obj, 'image', None)
        if not image:
            return None

        try:
            url = str(image.url)
        except Exception:
            return None

        if not url:
            return None

        if url.startswith(('http://', 'https://')):
            return url

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(url)

        return url

    def get_image(self, obj):
        return self._get_image_url(obj)

    def get_img(self, obj):
        return self._get_image_url(obj)

    def get_image_url(self, obj):
        return self._get_image_url(obj)

    def get_imageUrl(self, obj):
        return self._get_image_url(obj)

    def get_download_url(self, obj):
        """
        Returns the best available download URL for paid users.
        Priority: download_url_override > ebook_file > file
        """
        return obj.downloadable_file


class OrderItemSerializer(serializers.ModelSerializer):
    product    = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model  = OrderItem
        fields = ['id', 'product', 'product_id', 'purchased']


class OrderSerializer(serializers.ModelSerializer):
    items    = OrderItemSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model  = Order
        fields = [
            'id', 'username', 'total_amount',
            'status', 'is_paid', 'phone',
            'created_at', 'items',
        ]


class RegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
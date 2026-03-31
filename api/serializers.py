from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Product, Order

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ProductSerializer(serializers.ModelSerializer):
    # Nest the category to provide full object details to the frontend
    category = CategorySerializer(read_only=True)
    
    # Ensure image URLs are absolute (includes http://localhost:8000)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 
            'name', 
            'description', 
            'price', 
            'image', 
            'stock', 
            'category', 
            'created_at'
        ]

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class OrderSerializer(serializers.ModelSerializer):
    # Display the username instead of just the user ID
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Order
        fields = [
            'id', 
            'user', 
            'total_amount', 
            'phone', 
            'checkout_request_id', 
            'transaction_id', 
            'status', 
            'is_paid', 
            'created_at'
        ]
        read_only_fields = ['checkout_request_id', 'transaction_id', 'status', 'is_paid']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
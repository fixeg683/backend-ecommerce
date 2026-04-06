from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
# Import the storage class for non-image files
from cloudinary_storage.storage import RawMediaCloudinaryStorage

class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    
    # Updated: Added RawMediaCloudinaryStorage to handle .exe and other binaries
    file = models.FileField(
        upload_to='products/files/',
        storage=RawMediaCloudinaryStorage(), 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(
            allowed_extensions=['exe', 'zip', 'dmg', 'sh', 'bin', 'msi']
        )]
    )
    stock = models.IntegerField(default=10)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# ... (Order and OrderItem models remain the same)
class Order(models.Model):
    STATUS = (
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone = models.CharField(max_length=15)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default='Pending')
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    purchased = models.BooleanField(default=False)

    class Meta:
        unique_together = ('order', 'product')

    def __str__(self):
        return f"{self.product.name} in {self.order}"
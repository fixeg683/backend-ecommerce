from django.db import models
from django.contrib.auth.models import User
from products.models import Product


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="orders")

    # Payment status
    is_paid = models.BooleanField(default=False)

    # Store external payment reference (PayPal / M-Pesa)
    payment_id = models.CharField(max_length=255, blank=True, null=True)

    # Optional fields for better tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - {self.product.name}"

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'product')  # Prevent duplicate purchases
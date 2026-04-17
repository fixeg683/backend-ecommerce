from django.db import models
from api.models import Product, Order

class Payment(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone = models.CharField(max_length=15)
    checkout_request_id = models.CharField(max_length=100, null=True, blank=True)
    mpesa_receipt_number = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Completed", "Completed"),
            ("Failed", "Failed"),
        ],
        default="Pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} - {self.status}"

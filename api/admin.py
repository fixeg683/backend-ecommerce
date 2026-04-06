from django.contrib import admin
from .models import Product, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "is_paid", "created_at")
    inlines = [OrderItemInline]


admin.site.register(Product)
admin.site.register(Order, OrderAdmin)
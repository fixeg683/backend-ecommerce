from django.contrib import admin
from .models import Category, Product, Order

# This makes the models visible in the Admin Panel
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'category', 'stock', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('price', 'stock') # Allows quick editing from the list view

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_amount', 'status', 'is_paid', 'created_at')
    list_filter = ('status', 'is_paid')
    readonly_fields = ('checkout_request_id',) # Prevents manual editing of IDs
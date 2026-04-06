from django.contrib import admin
from django.utils.html import format_html
from .models import Product, Order, OrderItem


# 🔹 PRODUCT ADMIN
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "file_link")
    search_fields = ("name",)
    list_filter = ("price",)

    def file_link(self, obj):
        """
        Display clickable download link in admin
        """
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Download File</a>',
                obj.file.url
            )
        return "No file"

    file_link.short_description = "File"


# 🔹 ORDER ITEM INLINE (shows products inside order)
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "purchased")


# 🔹 ORDER ADMIN
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "is_paid", "created_at")
    list_filter = ("is_paid", "created_at")
    search_fields = ("user__username",)
    inlines = [OrderItemInline]


# 🔹 REGISTER MODELS
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
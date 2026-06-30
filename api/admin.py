from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ("id", "name")
    search_fields = ("name",)
    ordering      = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display   = ("name", "product_type", "price", "category", "author", "file_link", "ebook_link")
    search_fields  = ("name", "category__name", "author")
    list_filter    = ("product_type", "category")
    autocomplete_fields = ["category"]

    fieldsets = (
        ("Basic Info", {
            "fields": ("name", "description", "price", "stock", "category", "product_type"),
        }),
        ("Media", {
            "fields": ("image",),
        }),
        ("Software / Game / Movie File", {
            "fields": ("file", "download_url_override"),
            "description": "Upload exe/zip/dmg or paste an external URL.",
        }),
        ("E-Book", {
            "fields": ("ebook_file", "author", "page_count"),
            "description": "Fill these fields for e-book products (PDF, ePub, MOBI).",
            "classes": ("collapse",),
        }),
    )

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">⬇ Software</a>', obj.file.url)
        if obj.download_url_override:
            return format_html('<a href="{}" target="_blank">🔗 External</a>', obj.download_url_override)
        return "—"
    file_link.short_description = "Download"

    def ebook_link(self, obj):
        if obj.ebook_file:
            return format_html('<a href="{}" target="_blank">📖 E-Book</a>', obj.ebook_file.url)
        return "—"
    ebook_link.short_description = "E-Book File"


class OrderItemInline(admin.TabularInline):
    model          = OrderItem
    extra          = 0
    readonly_fields = ("product", "purchased")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ("id", "user", "is_paid", "status", "created_at")
    list_filter   = ("is_paid", "status", "created_at")
    search_fields = ("user__username",)
    inlines       = [OrderItemInline]


admin.site.register(OrderItem)
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.core.files.storage import FileSystemStorage

try:
    from cloudinary_storage.storage import RawMediaCloudinaryStorage
except ImportError:  # pragma: no cover - optional dependency
    class RawMediaCloudinaryStorage(FileSystemStorage):
        pass


digital_file_validator = FileExtensionValidator(
    allowed_extensions=[
        # Software
        'exe',
        'zip',
        'dmg',
        'sh',
        'bin',
        'msi',

        # Videos
        'mp4',
        'mkv',

        # Documents / ebooks
        'pdf',
        'epub',
        'doc',
        'docx',

        # Archives
        'rar',
        '7z'
    ]
)


class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):

    PRODUCT_TYPE_CHOICES = [
        ("software", "Software"),
        ("game",     "Game"),
        ("movie",    "Movie"),
        ("ebook",    "E-Book"),
    ]

    name        = models.CharField(max_length=200)
    description = models.TextField()
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPE_CHOICES,
        default="software",
        help_text="Type of digital product",
    )

    # Cover image (all product types)
    image = models.ImageField(upload_to='products/', null=True, blank=True)

    # Software / Game / Movie file (exe, zip, dmg, etc.)
    # ⚠️  Cloudinary free plan caps uploads at 100 MB.
    # For files > 100 MB use "Download url override" and host on Google Drive / Mega / S3.
    file = models.FileField(
        upload_to='products/files/',
        storage=RawMediaCloudinaryStorage(),
        null=True,
        blank=True,
        validators=[digital_file_validator],
        help_text="Direct upload (max ~100 MB). Use 'Download url override' for larger files.",
    )

    download_url_override = models.URLField(
        null=True,
        blank=True,
        help_text="External download URL (overrides Cloudinary file if set)"
    )

    stock = models.IntegerField(default=10)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def downloadable_file(self):
        """Returns the best available download URL."""
        if self.download_url_override:
            return self.download_url_override
        if self.product_type == "ebook" and self.ebook_file:
            return self.ebook_file.url
        if self.file:
            return self.file.url
        return None

    @property
    def is_ebook(self):
        return self.product_type == "ebook"

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS = (
        ('Pending',   'Pending'),
        ('Completed', 'Completed'),
        ('Failed',    'Failed'),
    )

    user               = models.ForeignKey(User, on_delete=models.CASCADE)
    total_amount       = models.DecimalField(max_digits=10, decimal_places=2)
    phone              = models.CharField(max_length=15)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    status             = models.CharField(max_length=20, choices=STATUS, default='Pending')
    is_paid            = models.BooleanField(default=False)
    created_at         = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"


class OrderItem(models.Model):
    order     = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product   = models.ForeignKey(Product, on_delete=models.CASCADE)
    purchased = models.BooleanField(default=False)

    class Meta:
        unique_together = ('order', 'product')

    def __str__(self):
        return f"{self.product.name} in {self.order}"
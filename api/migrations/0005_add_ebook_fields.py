# Generated migration — adds e-book support to Product model

from django.db import migrations, models
import cloudinary_storage.storage
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_product_download_url_override"),
    ]

    operations = [
        # 1. Add product_type field so admin/frontend can distinguish ebook vs software
        migrations.AddField(
            model_name="product",
            name="product_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("software", "Software"),
                    ("game",     "Game"),
                    ("movie",    "Movie"),
                    ("ebook",    "E-Book"),
                ],
                default="software",
                help_text="Type of digital product",
            ),
        ),

        # 2. Add dedicated ebook_file field that accepts PDF & ePub
        migrations.AddField(
            model_name="product",
            name="ebook_file",
            field=models.FileField(
                upload_to="products/ebooks/",
                storage=cloudinary_storage.storage.RawMediaCloudinaryStorage(),
                null=True,
                blank=True,
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=["pdf", "epub", "mobi"]
                    )
                ],
                help_text="Upload PDF, ePub or MOBI file for e-books",
            ),
        ),

        # 3. Add author field (relevant for ebooks)
        migrations.AddField(
            model_name="product",
            name="author",
            field=models.CharField(
                max_length=200,
                blank=True,
                default="",
                help_text="Book author (for e-books)",
            ),
        ),

        # 4. Add page_count field
        migrations.AddField(
            model_name="product",
            name="page_count",
            field=models.PositiveIntegerField(
                null=True,
                blank=True,
                help_text="Number of pages (for e-books)",
            ),
        ),
    ]
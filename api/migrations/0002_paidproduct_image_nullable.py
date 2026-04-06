# api/migrations/0002_paidproduct_image_nullable.py

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Make image nullable
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(
                upload_to='products/',
                null=True,
                blank=True,
            ),
        ),

        # ✅ REMOVED duplicate 'file' field (THIS FIXES YOUR ERROR)

        # 2. Create PaidProduct model
        migrations.CreateModel(
            name='PaidProduct',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('paid_at', models.DateTimeField(auto_now_add=True)),
                (
                    'order',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to='api.order',
                    ),
                ),
                (
                    'product',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to='api.product',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'unique_together': {('user', 'product')},
            },
        ),
    ]
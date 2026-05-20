from django.db import migrations

def create_default_categories(apps, schema_editor):
    Category = apps.get_model('api', 'Category')
    categories = ["Softwares", "Games", "Movies", "E-book"]
    for name in categories:
        Category.objects.get_or_create(name=name)

def reverse_default_categories(apps, schema_editor):
    Category = apps.get_model('api', 'Category')
    Category.objects.filter(name__in=["Softwares", "Games", "Movies", "E-book"]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_add_ebook_fields'),
    ]

    operations = [
        migrations.RunPython(create_default_categories, reverse_default_categories),
    ]

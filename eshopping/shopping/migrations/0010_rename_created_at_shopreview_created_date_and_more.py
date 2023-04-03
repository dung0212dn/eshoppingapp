# Generated by Django 4.1.7 on 2023-03-25 08:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shopping', '0009_rename_created_at_productreview_created_date_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='shopreview',
            old_name='created_at',
            new_name='created_date',
        ),
        migrations.AddField(
            model_name='shopreview',
            name='active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='shopreview',
            name='updated_date',
            field=models.DateTimeField(auto_now=True),
        ),
    ]

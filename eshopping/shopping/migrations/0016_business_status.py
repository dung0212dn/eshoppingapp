# Generated by Django 4.1.7 on 2023-03-27 16:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shopping', '0015_alter_orderdetail_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='business',
            name='status',
            field=models.CharField(choices=[('confirmed', 'Confirmed'), ('unconfirmed', 'Unconfirmed')], default='unconfirmed', max_length=20),
        ),
    ]

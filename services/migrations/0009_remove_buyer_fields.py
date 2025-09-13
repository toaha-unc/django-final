# Generated manually to remove buyer fields from Order model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0008_payment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='buyer_name',
        ),
        migrations.RemoveField(
            model_name='order',
            name='buyer_phone',
        ),
        migrations.RemoveField(
            model_name='order',
            name='buyer_address',
        ),
        migrations.RemoveField(
            model_name='order',
            name='buyer_city',
        ),
        migrations.RemoveField(
            model_name='order',
            name='buyer_country',
        ),
        migrations.RemoveField(
            model_name='order',
            name='buyer_postal_code',
        ),
    ]

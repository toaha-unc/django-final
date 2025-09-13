# Generated manually for buyer address fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0006_payment_paymentmethod'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='buyer_name',
            field=models.CharField(blank=True, help_text="Buyer's full name", max_length=200),
        ),
        migrations.AddField(
            model_name='order',
            name='buyer_phone',
            field=models.CharField(blank=True, help_text="Buyer's phone number", max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='buyer_address',
            field=models.TextField(blank=True, help_text="Buyer's address"),
        ),
        migrations.AddField(
            model_name='order',
            name='buyer_city',
            field=models.CharField(blank=True, help_text="Buyer's city", max_length=100),
        ),
        migrations.AddField(
            model_name='order',
            name='buyer_country',
            field=models.CharField(blank=True, help_text="Buyer's country", max_length=100),
        ),
        migrations.AddField(
            model_name='order',
            name='buyer_postal_code',
            field=models.CharField(blank=True, help_text="Buyer's postal code", max_length=20),
        ),
    ]

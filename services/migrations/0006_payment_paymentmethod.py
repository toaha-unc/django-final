# Generated manually for Payment and PaymentMethod models

from django.db import migrations, models
import django.db.models.deletion
import uuid
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_user_managers'),
        ('services', '0005_buyerprofile_buyeranalytics_buyerpreferences_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('payment_id', models.CharField(blank=True, max_length=100, unique=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='BDT', max_length=3)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('refunded', 'Refunded')], default='pending', max_length=20)),
                ('sslcommerz_session_key', models.CharField(blank=True, max_length=100)),
                ('sslcommerz_tran_id', models.CharField(blank=True, max_length=100)),
                ('sslcommerz_val_id', models.CharField(blank=True, max_length=100)),
                ('sslcommerz_bank_tran_id', models.CharField(blank=True, max_length=100)),
                ('sslcommerz_card_type', models.CharField(blank=True, max_length=50)),
                ('sslcommerz_card_no', models.CharField(blank=True, max_length=50)),
                ('sslcommerz_card_issuer', models.CharField(blank=True, max_length=100)),
                ('sslcommerz_card_brand', models.CharField(blank=True, max_length=50)),
                ('sslcommerz_card_issuer_country', models.CharField(blank=True, max_length=100)),
                ('sslcommerz_card_issuer_country_code', models.CharField(blank=True, max_length=10)),
                ('sslcommerz_currency_type', models.CharField(blank=True, max_length=10)),
                ('sslcommerz_currency_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('sslcommerz_currency_rate', models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True)),
                ('sslcommerz_base_fair', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('sslcommerz_discount_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('sslcommerz_risk_level', models.CharField(blank=True, max_length=20)),
                ('sslcommerz_risk_title', models.CharField(blank=True, max_length=100)),
                ('gateway_response', models.JSONField(blank=True, default=dict)),
                ('failure_reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='accounts.user')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='services.order')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('gateway', models.CharField(max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('configuration', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
    ]

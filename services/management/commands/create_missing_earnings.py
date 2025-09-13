from django.core.management.base import BaseCommand
from django.db import transaction
from services.models import Order, SellerEarnings
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create missing SellerEarnings records for completed orders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating records',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find completed orders that don't have earnings records
        completed_orders = Order.objects.filter(status='completed')
        missing_earnings = []
        
        for order in completed_orders:
            if not SellerEarnings.objects.filter(seller=order.seller, order=order).exists():
                missing_earnings.append(order)
        
        self.stdout.write(f"Found {len(missing_earnings)} completed orders without earnings records")
        
        if dry_run:
            self.stdout.write("DRY RUN - No records will be created")
            for order in missing_earnings:
                self.stdout.write(f"Would create earnings for Order {order.order_number} - {order.service.title} - BDT {order.total_amount}")
        else:
            created_count = 0
            with transaction.atomic():
                for order in missing_earnings:
                    try:
                        SellerEarnings.objects.create(
                            seller=order.seller,
                            order=order,
                            gross_amount=order.total_amount,
                            platform_fee=order.total_amount * Decimal('0.10'),  # 10% platform fee
                            net_amount=order.total_amount * Decimal('0.90')  # 90% to seller
                        )
                        created_count += 1
                        self.stdout.write(f"Created earnings for Order {order.order_number} - BDT {order.total_amount}")
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Failed to create earnings for Order {order.order_number}: {e}")
                        )
            
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created {created_count} earnings records")
            )

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import UserProfile

User = get_user_model()

class Command(BaseCommand):
    help = 'Create test users for the freelancer platform'

    def handle(self, *args, **options):
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            email='admin@gmail.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'seller',
                'is_staff': True,
                'is_superuser': True,
                'is_email_verified': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            UserProfile.objects.create(user=admin_user)
            self.stdout.write(
                self.style.SUCCESS('Successfully created admin user')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Admin user already exists')
            )

        # Create seller user
        seller_user, created = User.objects.get_or_create(
            email='supabase_seller@example.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'Seller',
                'role': 'seller',
                'is_email_verified': True,
            }
        )
        if created:
            seller_user.set_password('seller123')
            seller_user.save()
            UserProfile.objects.create(user=seller_user)
            self.stdout.write(
                self.style.SUCCESS('Successfully created seller user')
            )
        else:
            # Update password if user exists
            seller_user.set_password('seller123')
            seller_user.is_email_verified = True
            seller_user.save()
            self.stdout.write(
                self.style.SUCCESS('Updated seller user password and verified email')
            )

        # Create buyer user
        buyer_user, created = User.objects.get_or_create(
            email='supabase_buyer@example.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'Buyer',
                'role': 'buyer',
                'is_email_verified': True,
            }
        )
        if created:
            buyer_user.set_password('buyer123')
            buyer_user.save()
            UserProfile.objects.create(user=buyer_user)
            self.stdout.write(
                self.style.SUCCESS('Successfully created buyer user')
            )
        else:
            # Update password if user exists
            buyer_user.set_password('buyer123')
            buyer_user.is_email_verified = True
            buyer_user.save()
            self.stdout.write(
                self.style.SUCCESS('Updated buyer user password and verified email')
            )

        self.stdout.write(
            self.style.SUCCESS('Test users created/updated successfully!')
        )
        self.stdout.write('Admin: admin@gmail.com / admin123')
        self.stdout.write('Seller: supabase_seller@example.com / seller123')
        self.stdout.write('Buyer: supabase_buyer@example.com / buyer123')

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User
import uuid
from django.utils import timezone
from decimal import Decimal

class Category(models.Model):
    """Service categories for filtering"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # For frontend icons
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Service(models.Model):
    """Digital service model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='services')
    
    # Basic service information
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    
    # Delivery and requirements
    delivery_time = models.PositiveIntegerField(help_text="Delivery time in days")
    requirements = models.TextField(blank=True, help_text="What the buyer needs to provide")
    
    # Service details
    features = models.JSONField(default=list, blank=True, help_text="List of features included in the service")
    images = models.JSONField(default=list, blank=True, help_text="List of image URLs")
    
    # Status and visibility
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Ratings and reviews
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} by {self.seller.email}"
    
    def update_rating_stats(self):
        """Update average rating and total reviews"""
        reviews = self.reviews.all()
        if reviews.exists():
            self.average_rating = sum(review.rating for review in reviews) / reviews.count()
            self.total_reviews = reviews.count()
        else:
            self.average_rating = 0.00
            self.total_reviews = 0
        self.save(update_fields=['average_rating', 'total_reviews'])

class ServiceImage(models.Model):
    """Service images for better presentation"""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='service_images')
    image_url = models.URLField()
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', 'created_at']
    
    def __str__(self):
        return f"Image for {self.service.title}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary image per service
        if self.is_primary:
            ServiceImage.objects.filter(service=self.service, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)

class Review(models.Model):
    """Review and rating model for services"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='reviews')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    
    # Rating and review details
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    title = models.CharField(max_length=200, help_text="Review title")
    comment = models.TextField(help_text="Detailed review comment")
    
    # Review status
    is_verified = models.BooleanField(default=False, help_text="Verified purchase review")
    is_helpful = models.PositiveIntegerField(default=0, help_text="Number of helpful votes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['service', 'buyer']  # One review per buyer per service
    
    def __str__(self):
        return f"{self.rating}★ review by {self.buyer.email} for {self.service.title}"
    
    def save(self, *args, **kwargs):
        # Set seller automatically
        if not self.seller_id:
            self.seller = self.service.seller
        
        # Update service rating stats when review is saved
        super().save(*args, **kwargs)
        self.service.update_rating_stats()
    
    def delete(self, *args, **kwargs):
        # Update service rating stats when review is deleted
        super().delete(*args, **kwargs)
        self.service.update_rating_stats()

class ReviewImage(models.Model):
    """Images attached to reviews"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField()
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Image for review by {self.review.buyer.email}"

class ReviewHelpful(models.Model):
    """Track helpful votes on reviews"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='helpful_votes_given')
    is_helpful = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['review', 'user']  # One vote per user per review
    
    def __str__(self):
        return f"{'Helpful' if self.is_helpful else 'Not helpful'} vote by {self.user.email}"
    
    def save(self, *args, **kwargs):
        # Update review helpful count
        super().save(*args, **kwargs)
        self.review.is_helpful = self.review.helpful_votes.filter(is_helpful=True).count()
        self.review.save(update_fields=['is_helpful'])

class Order(models.Model):
    """Order model for service purchases"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('review', 'In Review'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('disputed', 'Disputed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='orders')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_placed')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_received')
    
    # Order details
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Order requirements and specifications
    requirements = models.TextField(help_text="Buyer's requirements for the service")
    special_instructions = models.TextField(blank=True, help_text="Additional instructions from buyer")
    
    # Delivery information
    expected_delivery_date = models.DateTimeField(null=True, blank=True)
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    
    # Order tracking
    placed_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Communication
    buyer_notes = models.TextField(blank=True, help_text="Notes from buyer")
    seller_notes = models.TextField(blank=True, help_text="Notes from seller")
    
    # Buyer contact and address information (temporarily disabled for production)
    # buyer_name = models.CharField(max_length=200, blank=True, help_text="Buyer's full name")
    # buyer_phone = models.CharField(max_length=20, blank=True, help_text="Buyer's phone number")
    # buyer_address = models.TextField(blank=True, help_text="Buyer's address")
    # buyer_city = models.CharField(max_length=100, blank=True, help_text="Buyer's city")
    # buyer_country = models.CharField(max_length=100, blank=True, help_text="Buyer's country")
    # buyer_postal_code = models.CharField(max_length=20, blank=True, help_text="Buyer's postal code")
    
    # Payment status (for future payment integration)
    is_paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['-placed_at']
    
    def __str__(self):
        return f"Order #{self.order_number} - {self.service.title}"
    
    def save(self, *args, **kwargs):
        # Generate order number if not exists
        if not self.order_number:
            self.order_number = f"ORD-{self.id.hex[:8].upper()}"
        
        # Set seller automatically
        if not self.seller_id:
            self.seller = self.service.seller
        
        # Set total amount if not set
        if not self.total_amount:
            self.total_amount = self.service.price
        
        # Update status based on timestamps
        if self.completed_at and self.status != 'completed':
            self.status = 'completed'
        elif self.cancelled_at and self.status != 'cancelled':
            self.status = 'cancelled'
        elif self.started_at and self.status == 'confirmed':
            self.status = 'in_progress'
        elif self.confirmed_at and self.status == 'pending':
            self.status = 'confirmed'
        
        super().save(*args, **kwargs)
    
    def get_status_display_name(self):
        """Get human-readable status name"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed']
    
    def can_be_completed(self):
        """Check if order can be marked as completed"""
        return self.status in ['in_progress', 'review']

class OrderMessage(models.Model):
    """Messages between buyer and seller for an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='order_messages_sent')
    message = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="Internal note not visible to other party")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.email} for Order #{self.order.order_number}"

class OrderFile(models.Model):
    """Files attached to orders (requirements, deliverables, etc.)"""
    FILE_TYPE_CHOICES = [
        ('requirement', 'Requirement'),
        ('deliverable', 'Deliverable'),
        ('reference', 'Reference'),
        ('other', 'Other'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='files')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='order_files_uploaded')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='other')
    file_name = models.CharField(max_length=255)
    file_url = models.URLField()
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.file_name} for Order #{self.order.order_number}"

class Notification(models.Model):
    """Notification system for order updates and other events"""
    NOTIFICATION_TYPES = [
        ('order_placed', 'Order Placed'),
        ('order_confirmed', 'Order Confirmed'),
        ('order_in_progress', 'Order In Progress'),
        ('order_completed', 'Order Completed'),
        ('order_cancelled', 'Order Cancelled'),
        ('order_message', 'New Order Message'),
        ('order_file', 'New Order File'),
        ('review_received', 'New Review Received'),
        ('service_featured', 'Service Featured'),
        ('system', 'System Notification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects (optional)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    review = models.ForeignKey(Review, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    
    # Notification status
    is_read = models.BooleanField(default=False)
    is_email_sent = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} notification for {self.recipient.email}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

class Recommendation(models.Model):
    """Service recommendations for users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='recommendations')
    score = models.FloatField(help_text="Recommendation score (0-1)")
    reason = models.CharField(max_length=200, help_text="Reason for recommendation")
    is_viewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-score', '-created_at']
        unique_together = ['user', 'service']  # One recommendation per user per service
    
    def __str__(self):
        return f"Recommendation for {self.user.email}: {self.service.title} (Score: {self.score})"

class SellerEarnings(models.Model):
    """Track seller earnings and financial data"""
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='earnings')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='earnings')
    
    # Financial details
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total order amount")
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, help_text="Platform commission")
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount after platform fee")
    
    # Payment status
    is_paid_out = models.BooleanField(default=False, help_text="Whether earnings have been paid out")
    paid_out_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['seller', 'order']  # One earnings record per order
    
    def __str__(self):
        return f"Earnings for {self.seller.email} - Order #{self.order.order_number}"
    
    def save(self, *args, **kwargs):
        # Calculate platform fee (10% for now, can be made configurable)
        if not self.platform_fee:
            from decimal import Decimal
            self.platform_fee = self.gross_amount * Decimal('0.10')
        
        # Calculate net amount
        self.net_amount = self.gross_amount - self.platform_fee
        
        super().save(*args, **kwargs)

class SellerAnalytics(models.Model):
    """Seller performance analytics and metrics"""
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analytics')
    
    # Service metrics
    total_services = models.PositiveIntegerField(default=0)
    active_services = models.PositiveIntegerField(default=0)
    featured_services = models.PositiveIntegerField(default=0)
    
    # Order metrics
    total_orders = models.PositiveIntegerField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)
    cancelled_orders = models.PositiveIntegerField(default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Review metrics
    total_reviews = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    five_star_reviews = models.PositiveIntegerField(default=0)
    four_star_reviews = models.PositiveIntegerField(default=0)
    three_star_reviews = models.PositiveIntegerField(default=0)
    two_star_reviews = models.PositiveIntegerField(default=0)
    one_star_reviews = models.PositiveIntegerField(default=0)
    
    # Financial metrics
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_platform_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    paid_out_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pending_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Time-based metrics
    orders_this_month = models.PositiveIntegerField(default=0)
    earnings_this_month = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    orders_this_year = models.PositiveIntegerField(default=0)
    earnings_this_year = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Seller Analytics"
        unique_together = ['seller']
    
    def __str__(self):
        return f"Analytics for {self.seller.email}"
    
    def update_analytics(self):
        """Update all analytics metrics for the seller"""
        from django.db.models import Avg, Count, Sum
        from django.utils import timezone
        from datetime import datetime
        
        # Service metrics
        services = self.seller.services.all()
        self.total_services = services.count()
        self.active_services = services.filter(is_active=True).count()
        self.featured_services = services.filter(is_featured=True).count()
        
        # Order metrics
        orders = self.seller.orders_received.all()
        self.total_orders = orders.count()
        self.completed_orders = orders.filter(status='completed').count()
        self.cancelled_orders = orders.filter(status='cancelled').count()
        
        # Average order value
        avg_order = orders.aggregate(avg_value=Avg('total_amount'))
        self.average_order_value = avg_order['avg_value'] or 0.00
        
        # Review metrics
        reviews = self.seller.reviews_received.all()
        self.total_reviews = reviews.count()
        
        if reviews.exists():
            avg_rating = reviews.aggregate(avg_rating=Avg('rating'))
            self.average_rating = avg_rating['avg_rating'] or 0.00
            
            # Rating distribution
            self.five_star_reviews = reviews.filter(rating=5).count()
            self.four_star_reviews = reviews.filter(rating=4).count()
            self.three_star_reviews = reviews.filter(rating=3).count()
            self.two_star_reviews = reviews.filter(rating=2).count()
            self.one_star_reviews = reviews.filter(rating=1).count()
        
        # Financial metrics
        earnings = self.seller.earnings.all()
        self.total_earnings = earnings.aggregate(total=Sum('net_amount'))['total'] or 0.00
        self.total_platform_fees = earnings.aggregate(total=Sum('platform_fee'))['total'] or 0.00
        self.net_earnings = earnings.aggregate(total=Sum('net_amount'))['total'] or 0.00
        self.paid_out_earnings = earnings.filter(is_paid_out=True).aggregate(total=Sum('net_amount'))['total'] or 0.00
        self.pending_earnings = earnings.filter(is_paid_out=False).aggregate(total=Sum('net_amount'))['total'] or 0.00
        
        # Time-based metrics
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        self.orders_this_month = orders.filter(placed_at__gte=start_of_month).count()
        self.earnings_this_month = earnings.filter(created_at__gte=start_of_month).aggregate(total=Sum('net_amount'))['total'] or 0.00
        
        self.orders_this_year = orders.filter(placed_at__gte=start_of_year).count()
        self.earnings_this_year = earnings.filter(created_at__gte=start_of_year).aggregate(total=Sum('net_amount'))['total'] or 0.00
        
        self.save()

class SellerProfile(models.Model):
    """Extended seller profile with business information"""
    seller = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    
    # Business information
    business_name = models.CharField(max_length=200, blank=True)
    business_description = models.TextField(blank=True)
    business_website = models.URLField(blank=True)
    business_phone = models.CharField(max_length=20, blank=True)
    business_address = models.TextField(blank=True)
    
    # Professional information
    skills = models.JSONField(default=list, blank=True, help_text="List of skills/expertise")
    experience_years = models.PositiveIntegerField(default=0, help_text="Years of experience")
    education = models.TextField(blank=True)
    certifications = models.JSONField(default=list, blank=True, help_text="List of certifications")
    
    # Social media and portfolio
    portfolio_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    behance_url = models.URLField(blank=True)
    
    # Business settings
    response_time = models.PositiveIntegerField(default=24, help_text="Average response time in hours")
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, help_text="Order completion rate percentage")
    on_time_delivery_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, help_text="On-time delivery rate percentage")
    
    # Availability
    is_available = models.BooleanField(default=True, help_text="Whether seller is accepting new orders")
    max_orders_per_month = models.PositiveIntegerField(default=10, help_text="Maximum orders per month")
    current_month_orders = models.PositiveIntegerField(default=0, help_text="Current month orders")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Seller Profile"
        verbose_name_plural = "Seller Profiles"
    
    def __str__(self):
        return f"Seller Profile for {self.seller.email}"
    
    def update_completion_rate(self):
        """Update completion rate based on order history"""
        orders = self.seller.orders_received.all()
        if orders.exists():
            completed = orders.filter(status='completed').count()
            total = orders.exclude(status='cancelled').count()
            if total > 0:
                self.completion_rate = (completed / total) * 100
                self.save(update_fields=['completion_rate'])
    
    def update_delivery_rate(self):
        """Update on-time delivery rate"""
        completed_orders = self.seller.orders_received.filter(status='completed')
        if completed_orders.exists():
            on_time = 0
            total = completed_orders.count()
            
            for order in completed_orders:
                if order.actual_delivery_date and order.expected_delivery_date:
                    if order.actual_delivery_date <= order.expected_delivery_date:
                        on_time += 1
            
            if total > 0:
                self.on_time_delivery_rate = (on_time / total) * 100
                self.save(update_fields=['on_time_delivery_rate'])

class BuyerProfile(models.Model):
    """Extended buyer profile with preferences and settings"""
    buyer = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer_profile')
    
    # Personal information
    company_name = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    company_size = models.CharField(max_length=50, blank=True, help_text="e.g., 1-10, 11-50, 51-200, 200+")
    
    # Preferences
    preferred_categories = models.JSONField(default=list, blank=True, help_text="List of preferred service categories")
    budget_range = models.CharField(max_length=50, blank=True, help_text="e.g., $100-500, $500-1000, $1000+")
    preferred_delivery_time = models.CharField(max_length=50, blank=True, help_text="e.g., 1-3 days, 1 week, 2 weeks+")
    
    # Communication preferences
    preferred_contact_method = models.CharField(max_length=20, default='email', choices=[
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('platform', 'Platform Messages')
    ])
    notification_preferences = models.JSONField(default=dict, blank=True, help_text="Notification settings")
    
    # Account settings
    is_active = models.BooleanField(default=True)
    auto_save_services = models.BooleanField(default=True, help_text="Automatically save viewed services")
    show_recommendations = models.BooleanField(default=True, help_text="Show personalized recommendations")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Buyer Profile"
        verbose_name_plural = "Buyer Profiles"
    
    def __str__(self):
        return f"Buyer Profile for {self.buyer.email}"

class SavedService(models.Model):
    """Services saved by buyers for later reference"""
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Personal notes about the service")
    
    class Meta:
        unique_together = ['buyer', 'service']
        ordering = ['-saved_at']
    
    def __str__(self):
        return f"{self.buyer.email} saved {self.service.title}"

class BuyerAnalytics(models.Model):
    """Analytics and statistics for buyers"""
    buyer = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer_analytics')
    
    # Order statistics
    total_orders = models.PositiveIntegerField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)
    cancelled_orders = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Review statistics
    total_reviews_given = models.PositiveIntegerField(default=0)
    average_rating_given = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    # Service interaction
    total_services_viewed = models.PositiveIntegerField(default=0)
    total_services_saved = models.PositiveIntegerField(default=0)
    favorite_categories = models.JSONField(default=list, blank=True, help_text="Most viewed/saved categories")
    
    # Time-based statistics
    orders_this_month = models.PositiveIntegerField(default=0)
    spent_this_month = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    orders_this_year = models.PositiveIntegerField(default=0)
    spent_this_year = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Activity metrics
    last_order_date = models.DateTimeField(null=True, blank=True)
    last_review_date = models.DateTimeField(null=True, blank=True)
    last_login_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Buyer Analytics"
        unique_together = ['buyer']
    
    def __str__(self):
        return f"Analytics for {self.buyer.email}"
    
    def update_analytics(self):
        """Update all analytics based on current data"""
        from django.db.models import Avg, Count, Sum
        
        # Order statistics
        orders = self.buyer.orders_placed.all()
        self.total_orders = orders.count()
        self.completed_orders = orders.filter(status='completed').count()
        self.cancelled_orders = orders.filter(status='cancelled').count()
        
        # Financial statistics
        completed_orders = orders.filter(status='completed')
        self.total_spent = completed_orders.aggregate(total=Sum('total_amount'))['total'] or 0.00
        self.average_order_value = completed_orders.aggregate(avg=Avg('total_amount'))['avg'] or 0.00
        
        # Review statistics
        reviews = self.buyer.reviews_given.all()
        self.total_reviews_given = reviews.count()
        self.average_rating_given = reviews.aggregate(avg=Avg('rating'))['avg'] or 0.00
        
        # Service interaction
        self.total_services_saved = self.buyer.saved_services.count()
        
        # Time-based statistics
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        self.orders_this_month = orders.filter(placed_at__gte=start_of_month).count()
        self.spent_this_month = completed_orders.filter(placed_at__gte=start_of_month).aggregate(total=Sum('total_amount'))['total'] or 0.00
        
        self.orders_this_year = orders.filter(placed_at__gte=start_of_year).count()
        self.spent_this_year = completed_orders.filter(placed_at__gte=start_of_year).aggregate(total=Sum('total_amount'))['total'] or 0.00
        
        # Activity dates
        if orders.exists():
            self.last_order_date = orders.order_by('-placed_at').first().placed_at
        
        if reviews.exists():
            self.last_review_date = reviews.order_by('-created_at').first().created_at
        
        self.save()

class BuyerPreferences(models.Model):
    """Detailed buyer preferences for personalized experience"""
    buyer = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer_preferences')
    
    # Service preferences
    preferred_service_types = models.JSONField(default=list, blank=True, help_text="Types of services preferred")
    preferred_seller_level = models.CharField(max_length=20, default='any', choices=[
        ('any', 'Any Level'),
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('expert', 'Expert')
    ])
    preferred_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, help_text="Minimum seller rating preferred")
    
    # Budget preferences
    min_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    preferred_currency = models.CharField(max_length=3, default='USD')
    
    # Communication preferences
    language_preference = models.CharField(max_length=10, default='en', help_text="Preferred language for communication")
    timezone = models.CharField(max_length=50, blank=True)
    response_time_preference = models.PositiveIntegerField(default=24, help_text="Preferred seller response time in hours")
    
    # Notification settings
    email_notifications = models.BooleanField(default=True)
    order_updates = models.BooleanField(default=True)
    new_services = models.BooleanField(default=True)
    recommendations = models.BooleanField(default=True)
    marketing_emails = models.BooleanField(default=False)
    
    # Privacy settings
    profile_visibility = models.CharField(max_length=20, default='public', choices=[
        ('public', 'Public'),
        ('private', 'Private'),
        ('sellers_only', 'Sellers Only')
    ])
    show_order_history = models.BooleanField(default=True)
    show_reviews = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Buyer Preferences"
        unique_together = ['buyer']
    
    def __str__(self):
        return f"Preferences for {self.buyer.email}"

# class Payment(models.Model):
#     """Payment model for SSLCommerz integration"""
#     # Temporarily disabled due to database schema issues
#     pass

# class PaymentMethod(models.Model):
#     """Payment method configuration"""
#     # Temporarily disabled due to database schema issues
#     pass

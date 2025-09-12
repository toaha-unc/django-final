from rest_framework import serializers
from .models import Category, Service, ServiceImage, Review, ReviewImage, ReviewHelpful, Order, OrderMessage, OrderFile, Notification, Recommendation, SellerEarnings, SellerAnalytics, SellerProfile, BuyerProfile, SavedService, BuyerAnalytics, BuyerPreferences
from accounts.serializers import UserSerializer

class CategorySerializer(serializers.ModelSerializer):
    service_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'icon', 'service_count', 'created_at']
    
    def get_service_count(self, obj):
        return obj.services.filter(is_active=True).count()

class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = ['id', 'image_url', 'caption', 'is_primary', 'created_at']

class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ['id', 'image_url', 'caption', 'created_at']

class ReviewHelpfulSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    
    class Meta:
        model = ReviewHelpful
        fields = ['id', 'user', 'is_helpful', 'created_at']
    
    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name
        }

class ReviewSerializer(serializers.ModelSerializer):
    buyer = serializers.SerializerMethodField()
    images = ReviewImageSerializer(many=True, read_only=True)
    helpful_votes = ReviewHelpfulSerializer(many=True, read_only=True)
    helpful_count = serializers.SerializerMethodField()
    user_has_voted = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = [
            'id', 'rating', 'title', 'comment', 'buyer', 'is_verified',
            'is_helpful', 'helpful_count', 'images', 'helpful_votes',
            'user_has_voted', 'user_vote', 'created_at', 'updated_at'
        ]
        read_only_fields = ['buyer', 'is_verified', 'is_helpful', 'helpful_count']
    
    def get_buyer(self, obj):
        return {
            'id': obj.buyer.id,
            'email': obj.buyer.email,
            'first_name': obj.buyer.first_name,
            'last_name': obj.buyer.last_name
        }
    
    def get_helpful_count(self, obj):
        return obj.helpful_votes.filter(is_helpful=True).count()
    
    def get_user_has_voted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.helpful_votes.filter(user=request.user).exists()
        return False
    
    def get_user_vote(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            vote = obj.helpful_votes.filter(user=request.user).first()
            if vote:
                return vote.is_helpful
        return None

class ReviewCreateSerializer(serializers.ModelSerializer):
    images = ReviewImageSerializer(many=True, required=False)
    
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment', 'images']
    
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        service = self.context['service']
        buyer = self.context['request'].user
        
        # Check if user has already reviewed this service
        if Review.objects.filter(service=service, buyer=buyer).exists():
            raise serializers.ValidationError("You have already reviewed this service")
        
        # Create review
        review = Review.objects.create(
            service=service,
            buyer=buyer,
            seller=service.seller,
            **validated_data
        )
        
        # Create review images
        for image_data in images_data:
            ReviewImage.objects.create(review=review, **image_data)
        
        return review

class OrderMessageSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderMessage
        fields = ['id', 'sender', 'message', 'is_internal', 'created_at']
        read_only_fields = ['sender', 'created_at']
    
    def get_sender(self, obj):
        return {
            'id': obj.sender.id,
            'email': obj.sender.email,
            'first_name': obj.sender.first_name,
            'last_name': obj.sender.last_name,
            'role': obj.sender.role
        }
    
    def create(self, validated_data):
        order = self.context['order']
        sender = self.context['request'].user
        
        # Check if user is part of the order
        if sender not in [order.buyer, order.seller]:
            raise serializers.ValidationError("You are not authorized to send messages for this order")
        
        return OrderMessage.objects.create(
            order=order,
            sender=sender,
            **validated_data
        )

class OrderFileSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderFile
        fields = ['id', 'file_type', 'file_name', 'file_url', 'file_size', 'description', 'uploaded_by', 'created_at']
        read_only_fields = ['uploaded_by', 'created_at']
    
    def get_uploaded_by(self, obj):
        return {
            'id': obj.uploaded_by.id,
            'email': obj.uploaded_by.email,
            'first_name': obj.uploaded_by.first_name,
            'last_name': obj.uploaded_by.last_name,
            'role': obj.uploaded_by.role
        }
    
    def create(self, validated_data):
        order = self.context['order']
        uploaded_by = self.context['request'].user
        
        # Check if user is part of the order
        if uploaded_by not in [order.buyer, order.seller]:
            raise serializers.ValidationError("You are not authorized to upload files for this order")
        
        return OrderFile.objects.create(
            order=order,
            uploaded_by=uploaded_by,
            **validated_data
        )

class OrderSerializer(serializers.ModelSerializer):
    """Serializer for listing orders"""
    service = serializers.SerializerMethodField()
    buyer = serializers.SerializerMethodField()
    seller = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display_name', read_only=True)
    can_be_cancelled = serializers.BooleanField(read_only=True)
    can_be_completed = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'service', 'buyer', 'seller', 'status', 'status_display',
            'total_amount', 'requirements', 'special_instructions', 'expected_delivery_date',
            'actual_delivery_date', 'placed_at', 'confirmed_at', 'started_at', 'completed_at',
            'cancelled_at', 'buyer_notes', 'seller_notes', 'is_paid', 'payment_method',
            'can_be_cancelled', 'can_be_completed'
        ]
        read_only_fields = ['order_number', 'total_amount', 'placed_at', 'confirmed_at', 'started_at', 'completed_at', 'cancelled_at']
    
    def get_service(self, obj):
        return {
            'id': obj.service.id,
            'title': obj.service.title,
            'price': obj.service.price,
            'delivery_time': obj.service.delivery_time,
            'category': obj.service.category.name
        }
    
    def get_buyer(self, obj):
        return {
            'id': obj.buyer.id,
            'email': obj.buyer.email,
            'first_name': obj.buyer.first_name,
            'last_name': obj.buyer.last_name
        }
    
    def get_seller(self, obj):
        return {
            'id': obj.seller.id,
            'email': obj.seller.email,
            'first_name': obj.seller.first_name,
            'last_name': obj.seller.last_name
        }

class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed order information"""
    service = serializers.SerializerMethodField()
    buyer = serializers.SerializerMethodField()
    seller = serializers.SerializerMethodField()
    messages = OrderMessageSerializer(many=True, read_only=True)
    files = OrderFileSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display_name', read_only=True)
    can_be_cancelled = serializers.BooleanField(read_only=True)
    can_be_completed = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'service', 'buyer', 'seller', 'status', 'status_display',
            'total_amount', 'requirements', 'special_instructions', 'expected_delivery_date',
            'actual_delivery_date', 'placed_at', 'confirmed_at', 'started_at', 'completed_at',
            'cancelled_at', 'buyer_notes', 'seller_notes', 'is_paid', 'payment_method',
            'messages', 'files', 'can_be_cancelled', 'can_be_completed'
        ]
        read_only_fields = ['order_number', 'total_amount', 'placed_at', 'confirmed_at', 'started_at', 'completed_at', 'cancelled_at']
    
    def get_service(self, obj):
        return {
            'id': obj.service.id,
            'title': obj.service.title,
            'description': obj.service.description,
            'price': obj.service.price,
            'delivery_time': obj.service.delivery_time,
            'category': obj.service.category.name,
            'seller': {
                'id': obj.service.seller.id,
                'email': obj.service.seller.email,
                'first_name': obj.service.seller.first_name,
                'last_name': obj.service.seller.last_name
            }
        }
    
    def get_buyer(self, obj):
        return {
            'id': obj.buyer.id,
            'email': obj.buyer.email,
            'first_name': obj.buyer.first_name,
            'last_name': obj.buyer.last_name
        }
    
    def get_seller(self, obj):
        return {
            'id': obj.seller.id,
            'email': obj.seller.email,
            'first_name': obj.seller.first_name,
            'last_name': obj.seller.last_name
        }

class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new orders"""
    
    class Meta:
        model = Order
        fields = ['service', 'requirements', 'special_instructions']
    
    def validate_service(self, value):
        # Check if service is active
        if not value.is_active:
            raise serializers.ValidationError("This service is not available")
        
        # Check if user is not the seller
        if value.seller == self.context['request'].user:
            raise serializers.ValidationError("You cannot order your own service")
        
        return value
    
    def create(self, validated_data):
        service = validated_data['service']
        buyer = self.context['request'].user
        
        # Check if user is a buyer
        if buyer.role != 'buyer':
            raise serializers.ValidationError("Only buyers can place orders")
        
        # Create order with minimal fields
        order = Order.objects.create(
            service=service,
            buyer=buyer,
            seller=service.seller,
            total_amount=service.price,
            requirements=validated_data.get('requirements', ''),
            special_instructions=validated_data.get('special_instructions', '')
        )
        
        return order

class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating orders (status changes, notes)"""
    
    class Meta:
        model = Order
        fields = ['status', 'buyer_notes', 'seller_notes']
    
    def validate_status(self, value):
        order = self.instance
        user = self.context['request'].user
        
        # Check if user is authorized to change status
        if user == order.buyer:
            # Buyers can only cancel orders
            if value not in ['cancelled']:
                raise serializers.ValidationError("Buyers can only cancel orders")
        elif user == order.seller:
            # Sellers can change status to confirmed, in_progress, review, completed
            if value not in ['confirmed', 'in_progress', 'review', 'completed']:
                raise serializers.ValidationError("Invalid status change for seller")
        else:
            raise serializers.ValidationError("You are not authorized to change this order status")
        
        return value

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'is_read', 'is_email_sent',
            'created_at', 'read_at'
        ]
        read_only_fields = ['notification_type', 'title', 'message', 'is_email_sent', 'created_at', 'read_at']

class RecommendationSerializer(serializers.ModelSerializer):
    """Serializer for service recommendations"""
    service = serializers.SerializerMethodField()
    
    class Meta:
        model = Recommendation
        fields = ['id', 'service', 'score', 'reason', 'is_viewed', 'created_at']
        read_only_fields = ['score', 'reason', 'created_at']
    
    def get_service(self, obj):
        return {
            'id': obj.service.id,
            'title': obj.service.title,
            'description': obj.service.description,
            'price': obj.service.price,
            'average_rating': obj.service.average_rating,
            'total_reviews': obj.service.total_reviews,
            'category': obj.service.category.name,
            'seller': {
                'id': obj.service.seller.id,
                'email': obj.service.seller.email,
                'first_name': obj.service.seller.first_name,
                'last_name': obj.service.seller.last_name
            }
        }

# Seller Dashboard Serializers
class SellerEarningsSerializer(serializers.ModelSerializer):
    """Serializer for seller earnings"""
    order = serializers.SerializerMethodField()
    
    class Meta:
        model = SellerEarnings
        fields = [
            'id', 'order', 'gross_amount', 'platform_fee', 'net_amount',
            'is_paid_out', 'paid_out_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['gross_amount', 'platform_fee', 'net_amount', 'created_at', 'updated_at']
    
    def get_order(self, obj):
        return {
            'id': obj.order.id,
            'order_number': obj.order.order_number,
            'service_title': obj.order.service.title,
            'buyer_name': f"{obj.order.buyer.first_name} {obj.order.buyer.last_name}",
            'status': obj.order.status,
            'placed_at': obj.order.placed_at
        }

class SellerAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for seller analytics"""
    
    class Meta:
        model = SellerAnalytics
        fields = [
            'total_services', 'active_services', 'featured_services',
            'total_orders', 'completed_orders', 'cancelled_orders', 'average_order_value',
            'total_reviews', 'average_rating', 'five_star_reviews', 'four_star_reviews',
            'three_star_reviews', 'two_star_reviews', 'one_star_reviews',
            'total_earnings', 'total_platform_fees', 'net_earnings',
            'paid_out_earnings', 'pending_earnings',
            'orders_this_month', 'earnings_this_month',
            'orders_this_year', 'earnings_this_year',
            'last_updated'
        ]
        read_only_fields = [
            'id', 'seller', 'total_services', 'active_services', 'featured_services',
            'total_orders', 'completed_orders', 'cancelled_orders', 'average_order_value',
            'total_reviews', 'average_rating', 'five_star_reviews', 'four_star_reviews',
            'three_star_reviews', 'two_star_reviews', 'one_star_reviews',
            'total_earnings', 'total_platform_fees', 'net_earnings',
            'paid_out_earnings', 'pending_earnings',
            'orders_this_month', 'earnings_this_month',
            'orders_this_year', 'earnings_this_year',
            'last_updated'
        ]

class SellerProfileSerializer(serializers.ModelSerializer):
    """Serializer for seller profile"""
    seller = UserSerializer(read_only=True)
    
    class Meta:
        model = SellerProfile
        fields = [
            'id', 'seller', 'business_name', 'business_description', 'business_website',
            'business_phone', 'business_address', 'skills', 'experience_years',
            'education', 'certifications', 'portfolio_url', 'linkedin_url',
            'github_url', 'behance_url', 'response_time', 'completion_rate',
            'on_time_delivery_rate', 'is_available', 'max_orders_per_month',
            'current_month_orders', 'created_at', 'updated_at'
        ]
        read_only_fields = ['seller', 'completion_rate', 'on_time_delivery_rate', 'created_at', 'updated_at']

class SellerProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating seller profile"""
    
    class Meta:
        model = SellerProfile
        fields = [
            'business_name', 'business_description', 'business_website',
            'business_phone', 'business_address', 'skills', 'experience_years',
            'education', 'certifications', 'portfolio_url', 'linkedin_url',
            'github_url', 'behance_url', 'response_time', 'is_available',
            'max_orders_per_month'
        ]

class ServiceListSerializer(serializers.ModelSerializer):
    """Serializer for listing services with basic information"""
    seller = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    orders_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Service
        fields = [
            'id', 'title', 'description', 'price', 'delivery_time',
            'seller', 'category', 'average_rating', 'total_reviews',
            'primary_image', 'is_featured', 'is_active', 'created_at', 'orders_count'
        ]
    
    def get_seller(self, obj):
        return {
            'id': obj.seller.id,
            'email': obj.seller.email,
            'first_name': obj.seller.first_name,
            'last_name': obj.seller.last_name,
            'role': obj.seller.role
        }
    
    def get_primary_image(self, obj):
        primary_image = obj.service_images.filter(is_primary=True).first()
        if primary_image:
            return ServiceImageSerializer(primary_image).data
        return None
    
    def get_orders_count(self, obj):
        return obj.orders.count()

class ServiceDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed service information"""
    seller = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    images = ServiceImageSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    review_stats = serializers.SerializerMethodField()
    user_can_review = serializers.SerializerMethodField()
    user_has_reviewed = serializers.SerializerMethodField()
    user_can_order = serializers.SerializerMethodField()
    orders_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Service
        fields = [
            'id', 'title', 'description', 'price', 'delivery_time',
            'requirements', 'features', 'seller', 'category', 'images',
            'average_rating', 'total_reviews', 'review_stats', 'reviews',
            'user_can_review', 'user_has_reviewed', 'user_can_order', 'is_active', 'is_featured',
            'created_at', 'updated_at', 'orders_count'
        ]
    
    def get_review_stats(self, obj):
        """Get detailed review statistics"""
        reviews = obj.reviews.all()
        if not reviews.exists():
            return {
                'average_rating': 0,
                'total_reviews': 0,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        
        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[i] = reviews.filter(rating=i).count()
        
        return {
            'average_rating': obj.average_rating,
            'total_reviews': obj.total_reviews,
            'rating_distribution': rating_distribution
        }
    
    def get_user_can_review(self, obj):
        """Check if current user can review this service"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        # Only buyers can review
        if request.user.role != 'buyer':
            return False
        
        # Check if user has already reviewed
        if obj.reviews.filter(buyer=request.user).exists():
            return False
        
        # Check if user has completed an order for this service
        if not obj.orders.filter(buyer=request.user, status='completed').exists():
            return False
        
        return True
    
    def get_user_has_reviewed(self, obj):
        """Check if current user has already reviewed this service"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        return obj.reviews.filter(buyer=request.user).exists()
    
    def get_user_can_order(self, obj):
        """Check if current user can order this service"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        # Only buyers can order
        if request.user.role != 'buyer':
            return False
        
        # Check if user is not the seller
        if request.user == obj.seller:
            return False
        
        # Check if service is active
        if not obj.is_active:
            return False
        
        return True
    
    def get_orders_count(self, obj):
        return obj.orders.count()

class ServiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new services"""
    images = ServiceImageSerializer(many=True, required=False)
    
    class Meta:
        model = Service
        fields = [
            'title', 'description', 'price', 'delivery_time',
            'requirements', 'features', 'category', 'images'
        ]
    
    def validate(self, attrs):
        # Ensure seller is set
        if not hasattr(self.context['request'].user, 'role') or self.context['request'].user.role != 'seller':
            raise serializers.ValidationError("Only sellers can create services")
        
        # Set default values for optional fields
        if 'requirements' not in attrs or not attrs['requirements']:
            attrs['requirements'] = ''
        if 'features' not in attrs:
            attrs['features'] = []
        
        return attrs
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        seller = self.context['request'].user
        
        # Ensure all required fields are present
        service_data = {
            'seller': seller,
            'title': validated_data.get('title'),
            'description': validated_data.get('description'),
            'price': validated_data.get('price'),
            'delivery_time': validated_data.get('delivery_time'),
            'category': validated_data.get('category'),
            'requirements': validated_data.get('requirements', ''),
            'features': validated_data.get('features', [])
        }
        
        service = Service.objects.create(**service_data)
        
        # Create service images
        for image_data in images_data:
            ServiceImage.objects.create(service=service, **image_data)
        
        return service
    
    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', [])
        
        # Update service fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update images if provided
        if images_data:
            # Clear existing images
            instance.service_images.all().delete()
            # Create new images
            for image_data in images_data:
                ServiceImage.objects.create(service=instance, **image_data)
        
        return instance

class ServiceFilterSerializer(serializers.Serializer):
    """Serializer for filtering and sorting services"""
    category = serializers.CharField(required=False, help_text="Filter by category name")
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=0)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=0)
    sort_by = serializers.ChoiceField(
        choices=[
            ('price_low', 'Price: Low to High'),
            ('price_high', 'Price: High to Low'),
            ('rating', 'Rating: High to Low'),
            ('newest', 'Newest First'),
            ('oldest', 'Oldest First'),
        ],
        required=False,
        default='newest'
    )
    search = serializers.CharField(required=False, help_text="Search in title and description")
    featured = serializers.BooleanField(required=False, help_text="Show only featured services")
    min_rating = serializers.IntegerField(required=False, min_value=1, max_value=5, help_text="Minimum rating filter")

class ReviewHelpfulCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating helpful votes on reviews"""
    
    class Meta:
        model = ReviewHelpful
        fields = ['is_helpful']
    
    def create(self, validated_data):
        review = self.context['review']
        user = self.context['request'].user
        
        # Check if user has already voted
        vote, created = ReviewHelpful.objects.get_or_create(
            review=review,
            user=user,
            defaults=validated_data
        )
        
        if not created:
            # Update existing vote
            vote.is_helpful = validated_data['is_helpful']
            vote.save()
        
        return vote

class BuyerProfileSerializer(serializers.ModelSerializer):
    """Serializer for buyer profile"""
    buyer = UserSerializer(read_only=True)
    
    class Meta:
        model = BuyerProfile
        fields = [
            'id', 'buyer', 'company_name', 'job_title', 'industry', 'company_size',
            'preferred_categories', 'budget_range', 'preferred_delivery_time',
            'preferred_contact_method', 'notification_preferences',
            'is_active', 'auto_save_services', 'show_recommendations',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'buyer', 'created_at', 'updated_at']

class BuyerProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating buyer profile"""
    
    class Meta:
        model = BuyerProfile
        fields = [
            'company_name', 'job_title', 'industry', 'company_size',
            'preferred_categories', 'budget_range', 'preferred_delivery_time',
            'preferred_contact_method', 'notification_preferences',
            'is_active', 'auto_save_services', 'show_recommendations'
        ]

class SavedServiceSerializer(serializers.ModelSerializer):
    """Serializer for saved services"""
    service = serializers.SerializerMethodField()
    
    class Meta:
        model = SavedService
        fields = ['id', 'service', 'saved_at', 'notes']
        read_only_fields = ['id', 'saved_at']
    
    def get_service(self, obj):
        from .serializers import ServiceListSerializer
        return ServiceListSerializer(obj.service, context=self.context).data

class SavedServiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating saved services"""
    
    class Meta:
        model = SavedService
        fields = ['service', 'notes']
    
    def validate_service(self, value):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Check if already saved
            if SavedService.objects.filter(buyer=request.user, service=value).exists():
                raise serializers.ValidationError("Service is already saved")
        return value
    
    def create(self, validated_data):
        validated_data['buyer'] = self.context['request'].user
        return super().create(validated_data)

class BuyerAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for buyer analytics"""
    
    class Meta:
        model = BuyerAnalytics
        fields = [
            'id', 'total_orders', 'completed_orders', 'cancelled_orders',
            'total_spent', 'average_order_value', 'total_reviews_given',
            'average_rating_given', 'total_services_viewed', 'total_services_saved',
            'favorite_categories', 'orders_this_month', 'spent_this_month',
            'orders_this_year', 'spent_this_year', 'last_order_date',
            'last_review_date', 'last_login_date', 'last_updated'
        ]
        read_only_fields = ['id', 'last_updated']

class BuyerPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for buyer preferences"""
    
    class Meta:
        model = BuyerPreferences
        fields = [
            'id', 'preferred_service_types', 'preferred_seller_level',
            'preferred_rating', 'min_budget', 'max_budget', 'preferred_currency',
            'language_preference', 'timezone', 'response_time_preference',
            'email_notifications', 'order_updates', 'new_services',
            'recommendations', 'marketing_emails', 'profile_visibility',
            'show_order_history', 'show_reviews', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class BuyerPreferencesUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating buyer preferences"""
    
    class Meta:
        model = BuyerPreferences
        fields = [
            'preferred_service_types', 'preferred_seller_level',
            'preferred_rating', 'min_budget', 'max_budget', 'preferred_currency',
            'language_preference', 'timezone', 'response_time_preference',
            'email_notifications', 'order_updates', 'new_services',
            'recommendations', 'marketing_emails', 'profile_visibility',
            'show_order_history', 'show_reviews'
        ]

class BuyerDashboardStatsSerializer(serializers.Serializer):
    """Serializer for buyer dashboard statistics"""
    total_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_reviews_given = serializers.IntegerField()
    average_rating_given = serializers.DecimalField(max_digits=3, decimal_places=2)
    total_services_saved = serializers.IntegerField()
    orders_this_month = serializers.IntegerField()
    spent_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    orders_this_year = serializers.IntegerField()
    spent_this_year = serializers.DecimalField(max_digits=12, decimal_places=2)
    favorite_categories = serializers.ListField(child=serializers.CharField())
    recent_orders = serializers.ListField()
    recent_reviews = serializers.ListField()
    saved_services_count = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    active_orders = serializers.IntegerField()

class BuyerOrderHistorySerializer(serializers.ModelSerializer):
    """Serializer for buyer order history"""
    service = serializers.SerializerMethodField()
    seller = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'service', 'seller', 'status', 'total_amount',
            'placed_at', 'expected_delivery_date', 'actual_delivery_date',
            'is_paid', 'payment_method'
        ]
    
    def get_service(self, obj):
        return {
            'id': obj.service.id,
            'title': obj.service.title,
            'category': obj.service.category.name,
            'price': obj.service.price
        }
    
    def get_seller(self, obj):
        return {
            'id': obj.seller.id,
            'email': obj.seller.email,
            'first_name': obj.seller.first_name,
            'last_name': obj.seller.last_name
        }

class BuyerReviewHistorySerializer(serializers.ModelSerializer):
    """Serializer for buyer review history"""
    service = serializers.SerializerMethodField()
    seller = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = [
            'id', 'rating', 'title', 'comment', 'service', 'seller',
            'is_verified', 'created_at', 'updated_at'
        ]
    
    def get_service(self, obj):
        return {
            'id': obj.service.id,
            'title': obj.service.title,
            'category': obj.service.category.name
        }
    
    def get_seller(self, obj):
        return {
            'id': obj.seller.id,
            'email': obj.seller.email,
            'first_name': obj.seller.first_name,
            'last_name': obj.seller.last_name
        }

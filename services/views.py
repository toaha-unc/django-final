from rest_framework import status, generics, filters, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Category, Service, ServiceImage, Review, ReviewImage, ReviewHelpful, Order, OrderMessage, OrderFile, Notification, Recommendation, SellerEarnings, SellerAnalytics, SellerProfile, BuyerProfile, SavedService, BuyerAnalytics, BuyerPreferences
from .serializers import (
    CategorySerializer, ServiceListSerializer, ServiceDetailSerializer,
    ServiceCreateSerializer, ServiceFilterSerializer, ReviewSerializer,
    ReviewCreateSerializer, ReviewHelpfulCreateSerializer, OrderSerializer,
    OrderDetailSerializer, OrderCreateSerializer, OrderUpdateSerializer,
    OrderMessageSerializer, OrderFileSerializer, NotificationSerializer,
    RecommendationSerializer, SellerEarningsSerializer, SellerAnalyticsSerializer,
    SellerProfileSerializer, SellerProfileUpdateSerializer, BuyerProfileSerializer,
    BuyerProfileUpdateSerializer, SavedServiceSerializer, SavedServiceCreateSerializer,
    BuyerAnalyticsSerializer, BuyerPreferencesSerializer, BuyerPreferencesUpdateSerializer,
    BuyerDashboardStatsSerializer, BuyerOrderHistorySerializer, BuyerReviewHistorySerializer
)

class CategoryListView(generics.ListAPIView):
    """List all categories"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

class ServiceListView(generics.ListAPIView):
    """List all services with filtering and sorting"""
    serializer_class = ServiceListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_featured']
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'average_rating', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Service.objects.filter(is_active=True).select_related('seller', 'category')
        
        # Apply filters from query parameters
        category = self.request.query_params.get('category', None)
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        featured = self.request.query_params.get('featured', None)
        search = self.request.query_params.get('search', None)
        sort_by = self.request.query_params.get('sort_by', 'newest')
        min_rating = self.request.query_params.get('min_rating', None)
        
        # Category filter
        if category:
            queryset = queryset.filter(category__name__iexact=category)
        
        # Price range filter
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Featured filter
        if featured and featured.lower() == 'true':
            queryset = queryset.filter(is_featured=True)
        
        # Search filter
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # Rating filter
        if min_rating:
            queryset = queryset.filter(average_rating__gte=min_rating)
        
        # Sorting
        if sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-average_rating')
        elif sort_by == 'oldest':
            queryset = queryset.order_by('created_at')
        else:  # newest (default)
            queryset = queryset.order_by('-created_at')
        
        return queryset

class ServiceDetailView(generics.RetrieveAPIView):
    """Get detailed service information"""
    queryset = Service.objects.filter(is_active=True).select_related('seller', 'category')
    serializer_class = ServiceDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'

class ServiceCreateView(generics.CreateAPIView):
    """Create a new service (Sellers only)"""
    serializer_class = ServiceCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Ensure only sellers can create services
        if self.request.user.role != 'seller':
            raise serializers.ValidationError("Only sellers can create services.")
        
        serializer.save(seller=self.request.user)

class ServiceUpdateView(generics.UpdateAPIView):
    """Update a service (Owner only)"""
    serializer_class = ServiceCreateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Service.objects.filter(seller=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save()

class ServiceDeleteView(generics.DestroyAPIView):
    """Delete a service (Owner only)"""
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Service.objects.filter(seller=self.request.user)
    
    def perform_destroy(self, instance):
        # Soft delete - just mark as inactive
        instance.is_active = False
        instance.save()

class SellerServicesView(generics.ListAPIView):
    """Get all services by a specific seller"""
    serializer_class = ServiceListSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        seller_id = self.kwargs.get('seller_id')
        return Service.objects.filter(
            seller_id=seller_id, 
            is_active=True
        ).select_related('seller', 'category')

class ReviewListView(generics.ListAPIView):
    """List reviews for a specific service"""
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        service_id = self.kwargs.get('service_id')
        service = get_object_or_404(Service, id=service_id)
        return Review.objects.filter(service=service).select_related('buyer', 'seller')

class ReviewCreateView(generics.CreateAPIView):
    """Create a review for a service (Buyers only)"""
    serializer_class = ReviewCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return context
        service_id = self.kwargs.get('service_id')
        service = get_object_or_404(Service, id=service_id)
        context['service'] = service
        return context
    
    def perform_create(self, serializer):
        # Ensure only buyers can create reviews
        if self.request.user.role != 'buyer':
            raise serializers.ValidationError("Only buyers can create reviews.")
        
        serializer.save()

class ReviewUpdateView(generics.UpdateAPIView):
    """Update a review (Owner only)"""
    serializer_class = ReviewCreateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Review.objects.filter(buyer=self.request.user)

class ReviewDeleteView(generics.DestroyAPIView):
    """Delete a review (Owner only)"""
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Review.objects.filter(buyer=self.request.user)

class ReviewHelpfulView(generics.CreateAPIView):
    """Mark a review as helpful or not helpful"""
    serializer_class = ReviewHelpfulCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return context
        review_id = self.kwargs.get('review_id')
        review = get_object_or_404(Review, id=review_id)
        context['review'] = review
        return context

class SellerReviewsView(generics.ListAPIView):
    """Get all reviews received by a seller"""
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        seller_id = self.kwargs.get('seller_id')
        return Review.objects.filter(
            seller_id=seller_id
        ).select_related('buyer', 'service')

# Order Views
class OrderListView(generics.ListAPIView):
    """List orders for the current user"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['placed_at', 'total_amount']
    ordering = ['-placed_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'buyer':
            return Order.objects.filter(buyer=user).select_related('service', 'seller')
        elif user.role == 'seller':
            return Order.objects.filter(seller=user).select_related('service', 'buyer')
        return Order.objects.none()

class OrderDetailView(generics.RetrieveAPIView):
    """Get detailed order information"""
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'buyer':
            return Order.objects.filter(buyer=user).select_related('service', 'seller')
        elif user.role == 'seller':
            return Order.objects.filter(seller=user).select_related('service', 'buyer')
        return Order.objects.none()

class OrderCreateView(generics.CreateAPIView):
    """Create a new order (Buyers only)"""
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        order = serializer.save()
        
        # Create notification for seller
        Notification.objects.create(
            recipient=order.seller,
            notification_type='order_placed',
            title='New Order Received',
            message=f'You have received a new order for "{order.service.title}" from {order.buyer.first_name} {order.buyer.last_name}.',
            order=order,
            service=order.service
        )

class OrderUpdateView(generics.UpdateAPIView):
    """Update order status and notes"""
    serializer_class = OrderUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'buyer':
            return Order.objects.filter(buyer=user)
        elif user.role == 'seller':
            return Order.objects.filter(seller=user)
        return Order.objects.none()
    
    def perform_update(self, serializer):
        order = self.get_object()
        old_status = order.status
        new_status = serializer.validated_data.get('status', old_status)
        
        # Update timestamps based on status change
        if new_status != old_status:
            if new_status == 'confirmed':
                order.confirmed_at = timezone.now()
            elif new_status == 'in_progress':
                order.started_at = timezone.now()
            elif new_status == 'completed':
                order.completed_at = timezone.now()
            elif new_status == 'cancelled':
                order.cancelled_at = timezone.now()
        
        order.save()
        
        # Create notification for status change
        if new_status != old_status:
            notification_data = {
                'order_confirmed': {
                    'title': 'Order Confirmed',
                    'message': f'Your order for "{order.service.title}" has been confirmed by the seller.'
                },
                'order_in_progress': {
                    'title': 'Order In Progress',
                    'message': f'Work has started on your order for "{order.service.title}".'
                },
                'order_completed': {
                    'title': 'Order Completed',
                    'message': f'Your order for "{order.service.title}" has been completed!'
                },
                'order_cancelled': {
                    'title': 'Order Cancelled',
                    'message': f'Your order for "{order.service.title}" has been cancelled.'
                }
            }
            
            if new_status in notification_data:
                data = notification_data[new_status]
                Notification.objects.create(
                    recipient=order.buyer,
                    notification_type=f'order_{new_status}',
                    title=data['title'],
                    message=data['message'],
                    order=order,
                    service=order.service
                )

class OrderMessageListView(generics.ListAPIView):
    """List messages for an order"""
    serializer_class = OrderMessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        order_id = self.kwargs.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        
        # Check if user is part of the order
        if self.request.user not in [order.buyer, order.seller]:
            return OrderMessage.objects.none()
        
        return OrderMessage.objects.filter(order=order).select_related('sender')

class OrderMessageCreateView(generics.CreateAPIView):
    """Create a message for an order"""
    serializer_class = OrderMessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return context
        order_id = self.kwargs.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        context['order'] = order
        return context
    
    def perform_create(self, serializer):
        message = serializer.save()
        
        # Create notification for the other party
        order = message.order
        recipient = order.seller if message.sender == order.buyer else order.buyer
        
        Notification.objects.create(
            recipient=recipient,
            notification_type='order_message',
            title='New Order Message',
            message=f'You have received a new message for order "{order.service.title}".',
            order=order,
            service=order.service
        )

class OrderFileListView(generics.ListAPIView):
    """List files for an order"""
    serializer_class = OrderFileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        order_id = self.kwargs.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        
        # Check if user is part of the order
        if self.request.user not in [order.buyer, order.seller]:
            return OrderFile.objects.none()
        
        return OrderFile.objects.filter(order=order).select_related('uploaded_by')

class OrderFileCreateView(generics.CreateAPIView):
    """Upload a file for an order"""
    serializer_class = OrderFileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Handle Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return context
        order_id = self.kwargs.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        context['order'] = order
        return context
    
    def perform_create(self, serializer):
        file_obj = serializer.save()
        
        # Create notification for the other party
        order = file_obj.order
        recipient = order.seller if file_obj.uploaded_by == order.buyer else order.buyer
        
        Notification.objects.create(
            recipient=recipient,
            notification_type='order_file',
            title='New Order File',
            message=f'A new file has been uploaded for order "{order.service.title}".',
            order=order,
            service=order.service
        )

# Notification Views
class NotificationListView(generics.ListAPIView):
    """List notifications for the current user"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['notification_type', 'is_read']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

class NotificationMarkReadView(generics.UpdateAPIView):
    """Mark notification as read"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    def perform_update(self, serializer):
        notification = self.get_object()
        notification.mark_as_read()

class NotificationMarkAllReadView(generics.UpdateAPIView):
    """Mark all notifications as read"""
    permission_classes = [IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return Response({'message': 'All notifications marked as read'})

# Recommendation Views
class RecommendationListView(generics.ListAPIView):
    """List service recommendations for the current user"""
    serializer_class = RecommendationSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-score', '-created_at']
    
    def get_queryset(self):
        return Recommendation.objects.filter(
            user=self.request.user,
            is_viewed=False
        ).select_related('service', 'service__seller', 'service__category')

class RecommendationMarkViewedView(generics.UpdateAPIView):
    """Mark recommendation as viewed"""
    serializer_class = RecommendationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Recommendation.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        recommendation = self.get_object()
        recommendation.is_viewed = True
        recommendation.save()

# Seller Dashboard Views
class SellerEarningsListView(generics.ListAPIView):
    """List earnings for the current seller"""
    serializer_class = SellerEarningsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_paid_out']
    ordering_fields = ['created_at', 'gross_amount', 'net_amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        if self.request.user.role != 'seller':
            return SellerEarnings.objects.none()
        return SellerEarnings.objects.filter(seller=self.request.user).select_related('order', 'order__service', 'order__buyer')

class SellerAnalyticsView(generics.RetrieveAPIView):
    """Get seller analytics and performance metrics"""
    serializer_class = SellerAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        if self.request.user.role != 'seller':
            return None
        
        # Get or create analytics for the seller
        analytics, created = SellerAnalytics.objects.get_or_create(seller=self.request.user)
        
        # Update analytics
        analytics.update_analytics()
        
        return analytics

class SellerProfileView(generics.RetrieveAPIView):
    """Get seller profile"""
    serializer_class = SellerProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        if self.request.user.role != 'seller':
            return None
        
        # Get or create seller profile
        profile, created = SellerProfile.objects.get_or_create(seller=self.request.user)
        
        # Update completion and delivery rates
        profile.update_completion_rate()
        profile.update_delivery_rate()
        
        return profile

class SellerProfileUpdateView(generics.UpdateAPIView):
    """Update seller profile"""
    serializer_class = SellerProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        if self.request.user.role != 'seller':
            return None
        
        profile, created = SellerProfile.objects.get_or_create(seller=self.request.user)
        return profile

class SellerServicesManagementView(generics.ListAPIView):
    """List seller's own services for management"""
    serializer_class = ServiceListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_featured', 'category']
    ordering_fields = ['created_at', 'price', 'average_rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        if self.request.user.role != 'seller':
            return Service.objects.none()
        return Service.objects.filter(seller=self.request.user).select_related('category')

class SellerOrdersManagementView(generics.ListAPIView):
    """List seller's orders for management"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'is_paid']
    ordering_fields = ['placed_at', 'total_amount']
    ordering = ['-placed_at']
    
    def get_queryset(self):
        if self.request.user.role != 'seller':
            return Order.objects.none()
        return Order.objects.filter(seller=self.request.user).select_related('service', 'buyer')

class SellerReviewsManagementView(generics.ListAPIView):
    """List reviews received by the seller"""
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['rating', 'is_verified']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        if self.request.user.role != 'seller':
            return Review.objects.none()
        return Review.objects.filter(seller=self.request.user).select_related('buyer', 'service')

@api_view(['GET'])
@permission_classes([AllowAny])
def service_stats(request):
    """Get service statistics"""
    total_services = Service.objects.filter(is_active=True).count()
    total_categories = Category.objects.count()
    featured_services = Service.objects.filter(is_active=True, is_featured=True).count()
    
    # Get category distribution
    categories = Category.objects.annotate(
        service_count=Count('services', filter=Q(services__is_active=True))
    ).values('name', 'service_count')
    
    return Response({
        'total_services': total_services,
        'total_categories': total_categories,
        'featured_services': featured_services,
        'categories': categories
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_featured(request, service_id):
    """Toggle featured status of a service (Admin only)"""
    service = get_object_or_404(Service, id=service_id)
    
    # Only allow admin or the service owner to toggle featured status
    if not request.user.is_staff and request.user != service.seller:
        return Response(
            {'error': 'You do not have permission to perform this action.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    service.is_featured = not service.is_featured
    service.save()
    
    return Response({
        'message': f'Service {"featured" if service.is_featured else "unfeatured"} successfully.',
        'is_featured': service.is_featured
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def review_stats(request, service_id):
    """Get detailed review statistics for a service"""
    service = get_object_or_404(Service, id=service_id)
    reviews = service.reviews.all()
    
    if not reviews.exists():
        return Response({
            'average_rating': 0,
            'total_reviews': 0,
            'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            'verified_reviews': 0
        })
    
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = reviews.filter(rating=i).count()
    
    verified_reviews = reviews.filter(is_verified=True).count()
    
    return Response({
        'average_rating': service.average_rating,
        'total_reviews': service.total_reviews,
        'rating_distribution': rating_distribution,
        'verified_reviews': verified_reviews
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_stats(request):
    """Get order statistics for the current user"""
    user = request.user
    
    if user.role == 'buyer':
        orders = Order.objects.filter(buyer=user)
    elif user.role == 'seller':
        orders = Order.objects.filter(seller=user)
    else:
        return Response({'error': 'Invalid user role'}, status=status.HTTP_400_BAD_REQUEST)
    
    total_orders = orders.count()
    pending_orders = orders.filter(status='pending').count()
    in_progress_orders = orders.filter(status='in_progress').count()
    completed_orders = orders.filter(status='completed').count()
    cancelled_orders = orders.filter(status='cancelled').count()
    
    total_spent = orders.filter(status='completed').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    return Response({
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'in_progress_orders': in_progress_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'total_spent': total_spent
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_recommendations(request):
    """Generate service recommendations for the current user"""
    user = request.user
    
    # Clear existing recommendations
    Recommendation.objects.filter(user=user).delete()
    
    # Simple recommendation algorithm based on user's order history
    if user.role == 'buyer':
        # Get categories from user's completed orders
        completed_orders = Order.objects.filter(
            buyer=user,
            status='completed'
        ).select_related('service__category')
        
        category_preferences = {}
        for order in completed_orders:
            category = order.service.category
            category_preferences[category.id] = category_preferences.get(category.id, 0) + 1
        
        # Generate recommendations based on preferences
        recommendations = []
        for category_id, preference_score in category_preferences.items():
            # Get services from preferred categories
            services = Service.objects.filter(
                category_id=category_id,
                is_active=True
            ).exclude(
                orders__buyer=user  # Exclude services user has already ordered
            ).distinct()[:5]
            
            for service in services:
                score = preference_score * 0.1 + service.average_rating * 0.2
                recommendations.append({
                    'user': user,
                    'service': service,
                    'score': min(score, 1.0),
                    'reason': f'Based on your interest in {service.category.name}'
                })
        
        # Create recommendation objects
        Recommendation.objects.bulk_create([
            Recommendation(**rec) for rec in recommendations
        ])
    
    return Response({
        'message': f'Generated {len(recommendations)} recommendations',
        'count': len(recommendations)
    })

# Seller Dashboard API Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seller_dashboard_stats(request):
    """Get comprehensive seller dashboard statistics"""
    if request.user.role != 'seller':
        return Response({'error': 'Only sellers can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get or create analytics
    analytics, created = SellerAnalytics.objects.get_or_create(seller=request.user)
    analytics.update_analytics()
    
    # Get recent orders
    recent_orders = Order.objects.filter(seller=request.user).order_by('-placed_at')[:5]
    
    # Get recent reviews
    recent_reviews = Review.objects.filter(seller=request.user).order_by('-created_at')[:5]
    
    # Get earnings summary
    earnings_summary = {
        'total_earnings': analytics.total_earnings,
        'this_month': analytics.earnings_this_month,
        'this_year': analytics.earnings_this_year,
        'pending_payout': analytics.pending_earnings,
        'paid_out': analytics.paid_out_earnings
    }
    
    # Get performance metrics
    performance_metrics = {
        'completion_rate': analytics.completed_orders / max(analytics.total_orders, 1) * 100,
        'average_rating': float(analytics.average_rating),
        'total_reviews': analytics.total_reviews,
        'response_time': 24,  # Default, can be updated from seller profile
        'on_time_delivery': 95.0  # Default, can be calculated from orders
    }
    
    return Response({
        'analytics': SellerAnalyticsSerializer(analytics).data,
        'recent_orders': OrderSerializer(recent_orders, many=True).data,
        'recent_reviews': ReviewSerializer(recent_reviews, many=True).data,
        'earnings_summary': earnings_summary,
        'performance_metrics': performance_metrics
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seller_earnings_summary(request):
    """Get seller earnings summary with time-based breakdown"""
    if request.user.role != 'seller':
        return Response({'error': 'Only sellers can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    from datetime import datetime, timedelta
    
    # Get earnings for different time periods
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    earnings = SellerEarnings.objects.filter(seller=request.user)
    
    # Calculate earnings for different periods
    monthly_earnings = earnings.filter(created_at__gte=start_of_month).aggregate(
        total=Sum('net_amount'),
        count=Count('id')
    )
    
    yearly_earnings = earnings.filter(created_at__gte=start_of_year).aggregate(
        total=Sum('net_amount'),
        count=Count('id')
    )
    
    all_time_earnings = earnings.aggregate(
        total=Sum('net_amount'),
        count=Count('id')
    )
    
    # Get pending vs paid out
    pending_earnings = earnings.filter(is_paid_out=False).aggregate(
        total=Sum('net_amount')
    )['total'] or 0
    
    paid_out_earnings = earnings.filter(is_paid_out=True).aggregate(
        total=Sum('net_amount')
    )['total'] or 0
    
    return Response({
        'monthly': {
            'earnings': monthly_earnings['total'] or 0,
            'orders': monthly_earnings['count'] or 0
        },
        'yearly': {
            'earnings': yearly_earnings['total'] or 0,
            'orders': yearly_earnings['count'] or 0
        },
        'all_time': {
            'earnings': all_time_earnings['total'] or 0,
            'orders': all_time_earnings['count'] or 0
        },
        'pending_payout': pending_earnings,
        'paid_out': paid_out_earnings
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_seller_availability(request):
    """Update seller availability status"""
    if request.user.role != 'seller':
        return Response({'error': 'Only sellers can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    is_available = request.data.get('is_available', True)
    
    profile, created = SellerProfile.objects.get_or_create(seller=request.user)
    profile.is_available = is_available
    profile.save()
    
    return Response({
        'message': f'Seller availability updated to {"available" if is_available else "unavailable"}',
        'is_available': is_available
    })

# Buyer Dashboard Views

class BuyerProfileView(generics.RetrieveAPIView):
    """Get buyer profile"""
    serializer_class = BuyerProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        profile, created = BuyerProfile.objects.get_or_create(buyer=self.request.user)
        return profile

class BuyerProfileUpdateView(generics.UpdateAPIView):
    """Update buyer profile"""
    serializer_class = BuyerProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        profile, created = BuyerProfile.objects.get_or_create(buyer=self.request.user)
        return profile

class SavedServiceListView(generics.ListAPIView):
    """List saved services for buyer"""
    serializer_class = SavedServiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SavedService.objects.filter(buyer=self.request.user).select_related('service', 'service__seller', 'service__category')

class SavedServiceCreateView(generics.CreateAPIView):
    """Save a service for later"""
    serializer_class = SavedServiceCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)

class SavedServiceDeleteView(generics.DestroyAPIView):
    """Remove a saved service"""
    queryset = SavedService.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SavedService.objects.filter(buyer=self.request.user)

class BuyerAnalyticsView(generics.RetrieveAPIView):
    """Get buyer analytics"""
    serializer_class = BuyerAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        analytics, created = BuyerAnalytics.objects.get_or_create(buyer=self.request.user)
        if created or self.request.query_params.get('update', False):
            analytics.update_analytics()
        return analytics

class BuyerPreferencesView(generics.RetrieveAPIView):
    """Get buyer preferences"""
    serializer_class = BuyerPreferencesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        preferences, created = BuyerPreferences.objects.get_or_create(buyer=self.request.user)
        return preferences

class BuyerPreferencesUpdateView(generics.UpdateAPIView):
    """Update buyer preferences"""
    serializer_class = BuyerPreferencesUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        preferences, created = BuyerPreferences.objects.get_or_create(buyer=self.request.user)
        return preferences

class BuyerOrderHistoryView(generics.ListAPIView):
    """Get buyer order history"""
    serializer_class = BuyerOrderHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Order.objects.filter(buyer=self.request.user).select_related('service', 'service__category', 'seller')
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-placed_at')

class BuyerReviewHistoryView(generics.ListAPIView):
    """Get buyer review history"""
    serializer_class = BuyerReviewHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Review.objects.filter(buyer=self.request.user).select_related('service', 'service__category', 'seller').order_by('-created_at')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buyer_dashboard_stats(request):
    """Get comprehensive buyer dashboard statistics"""
    if request.user.role != 'buyer':
        return Response({'error': 'Only buyers can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get or create analytics
    analytics, created = BuyerAnalytics.objects.get_or_create(buyer=request.user)
    if created or request.query_params.get('update', False):
        analytics.update_analytics()
    
    # Get recent orders
    recent_orders = Order.objects.filter(buyer=request.user).select_related('service', 'seller').order_by('-placed_at')[:5]
    
    # Get recent reviews
    recent_reviews = Review.objects.filter(buyer=request.user).select_related('service', 'seller').order_by('-created_at')[:5]
    
    # Get saved services count
    saved_services_count = SavedService.objects.filter(buyer=request.user).count()
    
    # Get pending and active orders
    pending_orders = Order.objects.filter(buyer=request.user, status='pending').count()
    active_orders = Order.objects.filter(buyer=request.user, status__in=['confirmed', 'in_progress', 'review']).count()
    
    # Prepare dashboard stats
    dashboard_stats = {
        'total_orders': analytics.total_orders,
        'completed_orders': analytics.completed_orders,
        'total_spent': analytics.total_spent,
        'average_order_value': analytics.average_order_value,
        'total_reviews_given': analytics.total_reviews_given,
        'average_rating_given': analytics.average_rating_given,
        'total_services_saved': analytics.total_services_saved,
        'orders_this_month': analytics.orders_this_month,
        'spent_this_month': analytics.spent_this_month,
        'orders_this_year': analytics.orders_this_year,
        'spent_this_year': analytics.spent_this_year,
        'favorite_categories': analytics.favorite_categories,
        'recent_orders': BuyerOrderHistorySerializer(recent_orders, many=True).data,
        'recent_reviews': BuyerReviewHistorySerializer(recent_reviews, many=True).data,
        'saved_services_count': saved_services_count,
        'pending_orders': pending_orders,
        'active_orders': active_orders
    }
    
    return Response(dashboard_stats)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buyer_spending_summary(request):
    """Get buyer spending summary with time-based breakdown"""
    if request.user.role != 'buyer':
        return Response({'error': 'Only buyers can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    from datetime import datetime, timedelta
    
    # Get orders for different time periods
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    orders = Order.objects.filter(buyer=request.user, status='completed')
    
    # Calculate spending for different periods
    monthly_spending = orders.filter(placed_at__gte=start_of_month).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    yearly_spending = orders.filter(placed_at__gte=start_of_year).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    all_time_spending = orders.aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Get spending by category
    spending_by_category = orders.values('service__category__name').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total')
    
    return Response({
        'monthly': {
            'spending': monthly_spending['total'] or 0,
            'orders': monthly_spending['count'] or 0
        },
        'yearly': {
            'spending': yearly_spending['total'] or 0,
            'orders': yearly_spending['count'] or 0
        },
        'all_time': {
            'spending': all_time_spending['total'] or 0,
            'orders': all_time_spending['count'] or 0
        },
        'by_category': spending_by_category
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_service_save(request):
    """Toggle save/unsave a service"""
    if request.user.role != 'buyer':
        return Response({'error': 'Only buyers can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    service_id = request.data.get('service_id')
    if not service_id:
        return Response({'error': 'service_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = Service.objects.get(id=service_id)
    except Service.DoesNotExist:
        return Response({'error': 'Service not found'}, status=status.HTTP_404_NOT_FOUND)
    
    saved_service = SavedService.objects.filter(buyer=request.user, service=service).first()
    
    if saved_service:
        # Unsave the service
        saved_service.delete()
        return Response({
            'message': 'Service removed from saved list',
            'is_saved': False
        })
    else:
        # Save the service
        notes = request.data.get('notes', '')
        SavedService.objects.create(buyer=request.user, service=service, notes=notes)
        return Response({
            'message': 'Service saved successfully',
            'is_saved': True
        })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buyer_activity_timeline(request):
    """Get buyer activity timeline"""
    if request.user.role != 'buyer':
        return Response({'error': 'Only buyers can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get recent activities
    orders = Order.objects.filter(buyer=request.user).order_by('-placed_at')[:10]
    reviews = Review.objects.filter(buyer=request.user).order_by('-created_at')[:10]
    saved_services = SavedService.objects.filter(buyer=request.user).order_by('-saved_at')[:10]
    
    # Combine and sort activities
    activities = []
    
    for order in orders:
        activities.append({
            'type': 'order',
            'action': f'Placed order for {order.service.title}',
            'date': order.placed_at,
            'data': BuyerOrderHistorySerializer(order).data
        })
    
    for review in reviews:
        activities.append({
            'type': 'review',
            'action': f'Reviewed {review.service.title}',
            'date': review.created_at,
            'data': BuyerReviewHistorySerializer(review).data
        })
    
    for saved in saved_services:
        activities.append({
            'type': 'saved',
            'action': f'Saved {saved.service.title}',
            'date': saved.saved_at,
            'data': SavedServiceSerializer(saved).data
        })
    
    # Sort by date
    activities.sort(key=lambda x: x['date'], reverse=True)
    
    return Response({
        'activities': activities[:20]  # Return last 20 activities
    })

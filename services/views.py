from rest_framework import status, generics, filters, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.db import transaction
import hashlib
import urllib.parse
import requests

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
    BuyerDashboardStatsSerializer, BuyerOrderHistorySerializer, BuyerReviewHistorySerializer,
    # PaymentMethodSerializer
)
from .sslcommerz_service import SSLCommerzService

class CategoryListView(generics.ListAPIView):
    """List all categories"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

class ServiceListView(generics.ListAPIView):
    """List all services with filtering and sorting"""
    serializer_class = ServiceListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]  # Removed OrderingFilter
    filterset_fields = ['category', 'is_featured']
    search_fields = ['title', 'description']

    def get_queryset(self):
        queryset = Service.objects.filter(is_active=True).select_related('seller', 'category').prefetch_related('orders')

        category = self.request.query_params.get('category')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        featured = self.request.query_params.get('featured')
        search = self.request.query_params.get('search')
        sort_by = self.request.query_params.get('sort_by', 'newest')
        min_rating = self.request.query_params.get('min_rating')

        if category:
            try:
                queryset = queryset.filter(category_id=int(category))
            except ValueError:
                queryset = queryset.filter(category__name__iexact=category)

        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass

        if featured and featured.lower() == 'true':
            queryset = queryset.filter(is_featured=True)

        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))

        if min_rating:
            try:
                queryset = queryset.filter(average_rating__gte=float(min_rating))
            except ValueError:
                pass

        # Manual, explicit ordering that won't be overridden
        if sort_by == 'price_low':
            return queryset.order_by('price', '-id')
        elif sort_by == 'price_high':
            return queryset.order_by('-price', '-id')
        elif sort_by == 'rating':
            return queryset.order_by('-average_rating', '-total_reviews', '-id')
        elif sort_by == 'oldest':
            return queryset.order_by('created_at', 'id')
        else:  # 'newest'
            return queryset.order_by('-created_at', '-id')

class ServiceDetailView(generics.RetrieveAPIView):
    """Get detailed service information"""
    queryset = Service.objects.filter(is_active=True).select_related('seller', 'category').prefetch_related('orders')
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
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Soft delete - just mark as inactive
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class SellerServicesView(generics.ListAPIView):
    """Get all services by a specific seller"""
    serializer_class = ServiceListSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        seller_id = self.kwargs.get('seller_id')
        return Service.objects.filter(
            seller_id=seller_id, 
            is_active=True
        ).select_related('seller', 'category').prefetch_related('orders')

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
    """Create a new order - minimal version for production"""
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            # Get basic data
            service_id = request.data.get('service')
            requirements = request.data.get('requirements', '')
            special_instructions = request.data.get('special_instructions', '')
            quantity = int(request.data.get('quantity', 1))
            total_amount = float(request.data.get('total_amount', 0))
            
            # Get service
            try:
                service = Service.objects.get(id=service_id, is_active=True)
            except Service.DoesNotExist:
                return Response({'error': 'Service not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Create order with minimal fields only
            order = Order.objects.create(
                service=service,
                buyer=request.user,
                seller=service.seller,
                total_amount=total_amount,
                requirements=requirements,
                special_instructions=special_instructions
            )
            
            # Create notification for seller about new order
            Notification.objects.create(
                recipient=service.seller,
                notification_type='order_placed',
                title='New Order Received',
                message=f'You have received a new order for "{service.title}" from {request.user.get_full_name() or request.user.email}.',
                order=order,
                service=service
            )
            
            # Create notification for buyer about order placement
            Notification.objects.create(
                recipient=request.user,
                notification_type='order_placed',
                title='Order Placed Successfully',
                message=f'Your order for "{service.title}" has been placed successfully.',
                order=order,
                service=service
            )
            
            return Response({
                'id': str(order.id),
                'service': str(order.service.id),
                'requirements': order.requirements,
                'special_instructions': order.special_instructions,
                'total_amount': float(order.total_amount),
                'status': order.status,
                'created_at': order.placed_at.isoformat()
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'Order creation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        # get the object BEFORE to compare
        order = self.get_object()
        old_status = order.status

        # this actually applies incoming changes (including status)
        order = serializer.save()
        new_status = order.status

        # update timestamps if status changed
        if new_status != old_status:
            now = timezone.now()
            if new_status == 'confirmed' and not order.confirmed_at:
                order.confirmed_at = now
            elif new_status == 'in_progress' and not order.started_at:
                order.started_at = now
            elif new_status == 'completed' and not order.completed_at:
                order.completed_at = now
            elif new_status == 'cancelled' and not order.cancelled_at:
                order.cancelled_at = now
            order.save(update_fields=['confirmed_at', 'started_at', 'completed_at', 'cancelled_at'])

            # Create seller earnings record when order is completed
            if new_status == 'completed':
                from .models import SellerEarnings
                from decimal import Decimal
                
                # Check if earnings record already exists
                if not SellerEarnings.objects.filter(seller=order.seller, order=order).exists():
                    SellerEarnings.objects.create(
                        seller=order.seller,
                        order=order,
                        gross_amount=order.total_amount,
                        platform_fee=order.total_amount * Decimal('0.10'),  # 10% platform fee
                        net_amount=order.total_amount * Decimal('0.90')  # 90% to seller
                    )
                    print(f"Created earnings record for order {order.order_number}")

            # notify buyer about the status change
            notification_data = {
                'confirmed':  ('Order Confirmed',  f'Your order for "{order.service.title}" has been confirmed by the seller.'),
                'in_progress':('Order In Progress',f'Work has started on your order for "{order.service.title}".'),
                'completed':  ('Order Completed',  f'Your order for "{order.service.title}" has been completed!'),
                'cancelled':  ('Order Cancelled',  f'Your order for "{order.service.title}" has been cancelled.')
            }
            if new_status in notification_data:
                title, message = notification_data[new_status]
                Notification.objects.create(
                    recipient=order.buyer,
                    title=title,
                    message=message,
                    notification_type=f'order_{new_status}',
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
        # Only show active services for management (soft-deleted services are hidden)
        return Service.objects.filter(seller=self.request.user, is_active=True).select_related('category').prefetch_related('orders')

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_recommendations(request):
    """Generate personalized recommendations for the user"""
    try:
        user = request.user
        recommendations = []
        
        if user.role == 'buyer':
            # Get user's order history to understand preferences
            user_orders = Order.objects.filter(buyer=user).select_related('service__category')
            ordered_categories = [order.service.category.id for order in user_orders]
            
            # Get recommended services
            if ordered_categories:
                # Services from categories user has ordered from with high ratings
                recommended_services = Service.objects.filter(
                    category_id__in=ordered_categories,
                    is_active=True,
                    average_rating__gte=4.0
                ).exclude(
                    orders__buyer=user  # Exclude already ordered services
                ).select_related('seller', 'category').order_by('-average_rating', '-total_reviews')[:5]
            else:
                # If no order history, recommend popular services
                recommended_services = Service.objects.filter(
                    is_active=True,
                    average_rating__gte=4.0
                ).exclude(
                    orders__buyer=user
                ).select_related('seller', 'category').order_by('-average_rating', '-total_reviews')[:5]
            
            # Create recommendation objects
            for service in recommended_services:
                recommendation, created = Recommendation.objects.get_or_create(
                    user=user,
                    service=service,
                    defaults={
                        'reason': f'Recommended based on your preferences',
                        'score': service.average_rating or 0
                    }
                )
                recommendations.append(recommendation)
        
        # Return recommendations
        serializer = RecommendationSerializer(recommendations, many=True, context={'request': request})
        return Response({
            'recommendations': serializer.data,
            'count': len(recommendations)
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Seller Dashboard API Views
@api_view(['GET'])
@permission_classes([AllowAny])
def test_cors_endpoint(request):
    """Test endpoint to check CORS configuration"""
    return Response({
        'message': 'CORS test endpoint working',
        'origin': request.META.get('HTTP_ORIGIN', 'No origin header'),
        'method': request.method,
        'headers': dict(request.META)
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def test_simple_endpoint(request):
    """Simple test endpoint without any models"""
    return Response({
        'message': 'Simple test successful',
        'status': 'ok'
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def test_minimal_endpoint(request):
    """Minimal test endpoint with no dependencies"""
    return Response({
        'message': 'Minimal test successful',
        'timestamp': '2025-09-13T04:45:00Z'
    })

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def test_redirect_endpoint(request):
    """Test redirect endpoint"""
    from django.http import HttpResponse
    html_content = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0; url=http://localhost:3000/payment-cancelled">
    </head>
    <body>
        <p>Test redirect to payment cancelled page...</p>
        <script>window.location.href = 'http://localhost:3000/payment-cancelled';</script>
    </body>
    </html>
    '''
    return HttpResponse(html_content, content_type='text/html')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_order_creation(request):
    """Test order creation with minimal approach"""
    try:
        # Just try to get a service first
        service = Service.objects.first()
        if not service:
            return Response({'error': 'No services found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Try to create a minimal order
        order = Order.objects.create(
            service=service,
            buyer=request.user,
            seller=service.seller,
            total_amount=100.0,
            requirements='test'
        )
        
        return Response({
            'message': 'Order created successfully',
            'order_id': str(order.id),
            'service_title': service.title
        })
        
    except Exception as e:
        return Response({
            'error': f'Order creation failed: {str(e)}',
            'error_type': type(e).__name__
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def seller_dashboard_stats(request):
    """Get comprehensive seller dashboard statistics"""
    if request.user.role != 'seller':
        return Response({'error': 'Only sellers can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Get or create analytics
        analytics, created = SellerAnalytics.objects.get_or_create(seller=request.user)
        analytics.update_analytics()
        
        # Get recent orders
        recent_orders = Order.objects.filter(seller=request.user).order_by('-placed_at')[:5]
        
        # Get recent reviews
        recent_reviews = Review.objects.filter(seller=request.user).order_by('-created_at')[:5]
        
        # Get earnings summary - fallback to direct calculation if no earnings records
        if analytics.total_earnings == 0:
            # Calculate revenue directly from completed orders
            from decimal import Decimal
            completed_orders = Order.objects.filter(seller=request.user, status='completed')
            total_revenue = completed_orders.aggregate(total=Sum('total_amount'))['total'] or 0
            platform_fee_rate = Decimal('0.10')  # 10% platform fee
            total_platform_fees = total_revenue * platform_fee_rate
            net_earnings = total_revenue - total_platform_fees
            
            earnings_summary = {
                'total_earnings': float(net_earnings),
                'this_month': float(analytics.earnings_this_month),
                'this_year': float(analytics.earnings_this_year),
                'pending_payout': float(net_earnings),  # All earnings are pending if no records exist
                'paid_out': 0.0
            }
        else:
            earnings_summary = {
                'total_earnings': float(analytics.total_earnings),
                'this_month': float(analytics.earnings_this_month),
                'this_year': float(analytics.earnings_this_year),
                'pending_payout': float(analytics.pending_earnings),
                'paid_out': float(analytics.paid_out_earnings)
            }
        
        # Get performance metrics
        total_orders = analytics.total_orders or 1
        completion_rate = (analytics.completed_orders / total_orders) * 100 if total_orders > 0 else 0
        
        performance_metrics = {
            'completion_rate': round(completion_rate, 2),
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
    except Exception as e:
        return Response({
            'error': f'Error loading dashboard stats: {str(e)}',
            'analytics': {},
            'recent_orders': [],
            'recent_reviews': [],
            'earnings_summary': {
                'total_earnings': 0.0,
                'this_month': 0.0,
                'this_year': 0.0,
                'pending_payout': 0.0,
                'paid_out': 0.0
            },
            'performance_metrics': {
                'completion_rate': 0.0,
                'average_rating': 0.0,
                'total_reviews': 0,
                'response_time': 24,
                'on_time_delivery': 95.0
            }
        }, status=status.HTTP_200_OK)

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
        # Return a simple profile object without database dependency
        return type('BuyerProfile', (), {
            'id': 1,
            'buyer': self.request.user,
            'company_name': '',
            'job_title': '',
            'industry': '',
            'company_size': '',
            'preferred_categories': [],
            'budget_range': '',
            'preferred_delivery_time': '',
            'preferred_contact_method': 'email',
            'notification_preferences': {},
            'is_active': True,
            'auto_save_services': True,
            'show_recommendations': True,
            'created_at': self.request.user.date_joined,
            'updated_at': self.request.user.date_joined
        })()

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
    
    try:
        # Get or create analytics
        analytics, created = BuyerAnalytics.objects.get_or_create(buyer=request.user)
        update_param = request.query_params.get('update', 'false').lower() == 'true'
        if created or update_param:
            analytics.update_analytics()
        
        # Get pending and active orders
        pending_orders = Order.objects.filter(buyer=request.user, status='pending').count()
        active_orders = Order.objects.filter(buyer=request.user, status__in=['confirmed', 'in_progress', 'review']).count()
        
        # Prepare dashboard stats
        dashboard_stats = {
            'total_orders': analytics.total_orders,
            'completed_orders': analytics.completed_orders,
            'total_spent': float(analytics.total_spent),
            'average_order_value': float(analytics.average_order_value),
            'total_reviews_given': analytics.total_reviews_given,
            'average_rating_given': float(analytics.average_rating_given),
            'total_services_saved': analytics.total_services_saved,
            'orders_this_month': analytics.orders_this_month,
            'spent_this_month': float(analytics.spent_this_month),
            'orders_this_year': analytics.orders_this_year,
            'spent_this_year': float(analytics.spent_this_year),
            'favorite_categories': analytics.favorite_categories or [],
            'last_order_date': analytics.last_order_date,
            'pending_orders': pending_orders,
            'active_orders': active_orders
        }
        
        return Response(dashboard_stats)
    except Exception as e:
        return Response({
            'error': f'Error loading dashboard stats: {str(e)}',
            'total_orders': 0,
            'completed_orders': 0,
            'total_spent': 0.0,
            'average_order_value': 0.0,
            'total_reviews_given': 0,
            'average_rating_given': 0.0,
            'total_services_saved': 0,
            'orders_this_month': 0,
            'spent_this_month': 0.0,
            'orders_this_year': 0,
            'spent_this_year': 0.0,
            'favorite_categories': [],
            'last_order_date': None,
            'recent_orders': [],
            'recent_reviews': [],
            'saved_services_count': 0,
            'pending_orders': 0,
            'active_orders': 0
        }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buyer_dashboard_stats_fresh(request):
    """Get fresh buyer dashboard statistics - always updates analytics"""
    if request.user.role != 'buyer':
        return Response({'error': 'Only buyers can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Always get or create analytics and update them
        analytics, created = BuyerAnalytics.objects.get_or_create(buyer=request.user)
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
            'total_spent': float(analytics.total_spent),
            'average_order_value': float(analytics.average_order_value),
            'total_reviews_given': analytics.total_reviews_given,
            'average_rating_given': float(analytics.average_rating_given),
            'total_services_saved': analytics.total_services_saved,
            'orders_this_month': analytics.orders_this_month,
            'spent_this_month': float(analytics.spent_this_month),
            'orders_this_year': analytics.orders_this_year,
            'spent_this_year': float(analytics.spent_this_year),
            'favorite_categories': analytics.favorite_categories or [],
            'last_order_date': analytics.last_order_date,
            'recent_orders': BuyerOrderHistorySerializer(recent_orders, many=True).data,
            'recent_reviews': BuyerReviewHistorySerializer(recent_reviews, many=True).data,
            'saved_services_count': saved_services_count,
            'pending_orders': pending_orders,
            'active_orders': active_orders
        }
        
        print(f"Fresh dashboard stats: {dashboard_stats}")
        return Response(dashboard_stats)
    except Exception as e:
        return Response({
            'error': f'Error loading dashboard stats: {str(e)}',
            'total_orders': 0,
            'completed_orders': 0,
            'total_spent': 0.0,
            'average_order_value': 0.0,
            'total_reviews_given': 0,
            'average_rating_given': 0.0,
            'total_services_saved': 0,
            'orders_this_month': 0,
            'spent_this_month': 0.0,
            'orders_this_year': 0,
            'spent_this_year': 0.0,
            'favorite_categories': [],
            'last_order_date': None,
            'recent_orders': [],
            'recent_reviews': [],
            'saved_services_count': 0,
            'pending_orders': 0,
            'active_orders': 0
        }, status=status.HTTP_200_OK)

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

# Payment Views
# class PaymentListView(generics.ListAPIView):
#     """List payments for the current user"""
#     serializer_class = PaymentSerializer
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
#     filterset_fields = ['status', 'currency']
#     ordering_fields = ['created_at', 'amount']
#     ordering = ['-created_at']
#     
#     def get_queryset(self):
#         return Payment.objects.filter(buyer=self.request.user).select_related('order', 'order__service')

# class PaymentDetailView(generics.RetrieveAPIView):
#     """Get detailed payment information"""
#     serializer_class = PaymentSerializer
#     permission_classes = [IsAuthenticated]
#     lookup_field = 'id'
#     
#     def get_queryset(self):
#         return Payment.objects.filter(buyer=self.request.user).select_related('order', 'order__service')

# class PaymentMethodListView(generics.ListAPIView):
#     """List available payment methods"""
#     serializer_class = PaymentMethodSerializer
#     permission_classes = [AllowAny]
#     
#     def get_queryset(self):
#         return PaymentMethod.objects.filter(is_active=True)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request, order_id):
    """Initiate payment for an order"""
    try:
        order = get_object_or_404(Order, id=order_id, buyer=request.user)
        
        # Check if order is already paid
        if order.is_paid:
            return Response({
                'error': 'Order is already paid'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if there's already a pending payment (temporarily disabled)
        # existing_payment = Payment.objects.filter(
        #     order=order, 
        #     status__in=['pending', 'processing']
        # ).first()
        
        # if existing_payment:
        #     return Response({
        #         'error': 'Payment already initiated for this order'
        #     }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create payment record (temporarily disabled due to database schema)
        # payment = Payment.objects.create(
        #     order=order,
        #     buyer=request.user,
        #     amount=order.total_amount,
        #     currency='BDT'
        # )
        
        # Mock payment data for testing
        payment_id = f"pay_{order.id.hex[:8]}"
        payment_uuid = f"uuid_{order.id.hex[:8]}"
        
        # Create SSLCommerz payment URL with proper parameters
        
        # SSLCommerz test credentials
        store_id = 'ts68c1700491a82'
        store_password = 'ts68c1700491a82@ssl'
        
        # Generate transaction ID
        tran_id = f"TXN_{order.id.hex[:8].upper()}_{int(timezone.now().timestamp())}"
        
        # Get customer data from user profile or use sensible defaults
        def get_customer_data(field_name, default_value='Not provided'):
            """Get customer data from user profile or return default"""
            try:
                if hasattr(order.buyer, 'profile') and order.buyer.profile:
                    return getattr(order.buyer.profile, field_name, '') or default_value
                return default_value
            except:
                return default_value
        
        # Prepare payment data
        payment_data = {
            'store_id': store_id,
            'store_passwd': store_password,
            'total_amount': str(order.total_amount),
            'currency': 'BDT',
            'tran_id': tran_id,
            'success_url': 'https://django-final-delta.vercel.app/api/payments/success/',
            'fail_url': 'https://django-final-delta.vercel.app/api/payments/failed/',
            'cancel_url': 'https://django-final-delta.vercel.app/api/payments/cancelled/',
            'ipn_url': 'https://django-final-delta.vercel.app/api/payments/success/',  # Required IPN URL
            'emi_option': '0',
            'multi_card_name': '',  # Force EasyCheckOut flow
            'cus_name': f"{order.buyer.first_name} {order.buyer.last_name}".strip() or order.buyer.email,
            'cus_email': order.buyer.email,
            'cus_add1': get_customer_data('address', 'Not provided'),
            'cus_add2': '',
            'cus_city': 'Not provided',  # UserProfile doesn't have city field
            'cus_state': 'Not provided',  # UserProfile doesn't have state field
            'cus_postcode': '0000',  # UserProfile doesn't have postal_code field
            'cus_country': 'Bangladesh',  # Default country for SSLCommerz
            'cus_phone': get_customer_data('phone_number', 'Not provided'),
            'cus_fax': '',
            'ship_name': f"{order.buyer.first_name} {order.buyer.last_name}".strip() or order.buyer.email,
            'ship_add1': get_customer_data('address', 'Not provided'),
            'ship_add2': '',
            'ship_city': 'Not provided',  # UserProfile doesn't have city field
            'ship_state': 'Not provided',  # UserProfile doesn't have state field
            'ship_postcode': '0000',  # UserProfile doesn't have postal_code field
            'ship_country': 'Bangladesh',  # Default country for SSLCommerz
            'shipping_method': 'NO',  # Digital services don't require shipping
            'product_name': order.service.title[:50],  # Product name for SSLCommerz
            'product_category': 'Digital Services',  # Product category for SSLCommerz
            'product_profile': 'non-physical-goods',  # Product profile for digital services
            'value_a': str(order.id),
            'value_b': payment_uuid,
            'value_c': order.order_number,
            'value_d': order.service.title[:50],
            'opt_a': '',  # Optional parameter A
            'opt_b': '',  # Optional parameter B
            'opt_c': '',  # Optional parameter C
            'opt_d': '',  # Optional parameter D
        }
        
        # Generate hash for SSLCommerz authentication
        # SSLCommerz hash format: store_password + tran_id + total_amount + currency
        hash_string = f"{store_password}{tran_id}{order.total_amount}BDT"
        payment_data['hash'] = hashlib.sha512(hash_string.encode()).hexdigest()
        
        # Debug: Print payment data for troubleshooting
        print(f"SSLCommerz Payment Data: {payment_data}")
        
        # Call SSLCommerz API to get the actual payment page URL
        try:
            import requests
            sslcommerz_url = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
            
            print(f"Calling SSLCommerz API to get payment page URL")
            print(f"Payment data being sent: {payment_data}")
            
            # Make API call to SSLCommerz
            response = requests.post(sslcommerz_url, data=payment_data, timeout=30)
            response.raise_for_status()
            
            sslcommerz_response = response.json()
            print(f"SSLCommerz API response: {sslcommerz_response}")
            
            if sslcommerz_response.get('status') == 'SUCCESS':
                gateway_url = sslcommerz_response.get('GatewayPageURL', '')
                print(f"SSLCommerz GatewayPageURL: {gateway_url}")
                
                if not gateway_url:
                    raise Exception("No GatewayPageURL received from SSLCommerz")
                
                result = {
                    'success': True,
                    'redirect_url': gateway_url,
                    'sessionkey': sslcommerz_response.get('sessionkey', tran_id),
                    'tran_id': tran_id,
                    'form_data': {},  # No need for form data since we have the direct URL
                    'store_id': store_id,
                    'store_password': store_password
                }
            else:
                error_msg = sslcommerz_response.get('failedreason', 'SSLCommerz API call failed')
                print(f"SSLCommerz API error: {error_msg}")
                raise Exception(f"SSLCommerz error: {error_msg}")
                
        except Exception as e:
            print(f"SSLCommerz API call failed: {e}")
            # Fallback to form submission approach
            sslcommerz_url = f"https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
            gateway_url = sslcommerz_url
            
            print(f"Falling back to SSLCommerz form submission approach")
            print(f"Payment data: {payment_data}")
            
            # Ensure all form_data values are strings for JSON serialization
            form_data_serializable = {k: str(v) for k, v in payment_data.items()}
            
            result = {
                'success': True,
                'redirect_url': gateway_url,
                'sessionkey': tran_id,
                'tran_id': tran_id,
                'form_data': form_data_serializable,
                'store_id': store_id,
                'store_password': store_password
            }
        
        if result['success']:
            response_data = {
                'payment_id': payment_id,
                'payment_uuid': payment_uuid,
                'redirect_url': result['redirect_url'],
                'session_key': result['sessionkey'],
                'tran_id': result['sessionkey'],
                'amount': float(order.total_amount),
                'currency': 'BDT',
                'order_number': order.order_number,
                'form_data': result['form_data']
            }
            print(f"Payment initiation response data: {response_data}")
            print(f"Response keys: {list(response_data.keys())}")
            print(f"Has redirect_url: {'redirect_url' in response_data}")
            print(f"Has form_data: {'form_data' in response_data}")
            return Response(response_data)
        else:
            return Response({
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def payment_success(request):
    """Handle SSLCommerz payment success callback"""
    try:
        print(f"=== PAYMENT SUCCESS CALLBACK ===")
        print(f"Request method: {request.method}")
        print(f"Request URL: {request.build_absolute_uri()}")
        print(f"Request data: {request.data}")
        print(f"Request query params: {request.query_params}")
        print(f"Request POST data: {request.POST}")
        print(f"Request GET data: {request.GET}")
        
        # Get order ID from SSLCommerz callback data
        order_id = None
        if request.method == 'POST':
            order_id = request.POST.get('value_a') or request.data.get('value_a')
        else:
            order_id = request.GET.get('value_a')
        
        print(f"Order ID from callback: {order_id}")
        
        if order_id:
            try:
                # Find the order and update its status
                order = Order.objects.get(id=order_id)
                print(f"Found order: {order.id}, current status: {order.status}")
                
                # Update order to confirmed and paid
                order.status = 'confirmed'
                order.is_paid = True
                order.payment_method = 'SSLCommerz'
                order.paid_at = timezone.now()
                order.save()
                
                print(f"Order {order.id} updated to confirmed and paid")
                
                # Notifications will be created by OrderUpdateView when status changes
                
            except Order.DoesNotExist:
                print(f"Order {order_id} not found")
            except Exception as e:
                print(f"Error updating order {order_id}: {e}")
        
        # Return HTML redirect instead of Django redirect
        from django.http import HttpResponse
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta http-equiv="refresh" content="0; url=http://localhost:3000/payment-success">
        </head>
        <body>
            <p>Redirecting to payment success page...</p>
            <script>window.location.href = 'http://localhost:3000/payment-success';</script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html')
    except Exception as e:
        print(f"Payment success error: {e}")
        from django.http import HttpResponse
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta http-equiv="refresh" content="0; url=http://localhost:3000/payment-success">
        </head>
        <body>
            <p>Redirecting to payment success page...</p>
            <script>window.location.href = 'http://localhost:3000/payment-success';</script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html')


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def payment_failed(request):
    """Handle SSLCommerz payment failed callback"""
    try:
        print(f"=== PAYMENT FAILED CALLBACK ===")
        print(f"Request method: {request.method}")
        print(f"Request data: {request.data}")
        print(f"Request query params: {request.query_params}")
        
        # Get order ID from SSLCommerz callback data
        order_id = None
        if request.method == 'POST':
            order_id = request.POST.get('value_a') or request.data.get('value_a')
        else:
            order_id = request.GET.get('value_a')
        
        print(f"Order ID from callback: {order_id}")
        
        if order_id:
            try:
                # Find the order and mark it as cancelled
                order = Order.objects.get(id=order_id)
                print(f"Found order: {order.id}, current status: {order.status}")
                
                # Update order to cancelled
                order.status = 'cancelled'
                order.cancelled_at = timezone.now()
                order.save()
                
                print(f"Order {order.id} marked as cancelled due to payment failure")
                
                # Create notification for buyer
                Notification.objects.create(
                    recipient=order.buyer,
                    notification_type='payment_failed',
                    title='Payment Failed',
                    message=f'Your payment for order #{order.order_number} has failed',
                    order=order,
                    service=order.service
                )
                
            except Order.DoesNotExist:
                print(f"Order {order_id} not found")
            except Exception as e:
                print(f"Error updating order {order_id}: {e}")
        
        # Return HTML redirect instead of Django redirect
        from django.http import HttpResponse
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta http-equiv="refresh" content="0; url=http://localhost:3000/payment-failed">
        </head>
        <body>
            <p>Redirecting to payment failed page...</p>
            <script>window.location.href = 'http://localhost:3000/payment-failed';</script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html')
    except Exception as e:
        print(f"Payment failed error: {e}")
        from django.http import HttpResponse
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta http-equiv="refresh" content="0; url=http://localhost:3000/payment-failed">
        </head>
        <body>
            <p>Redirecting to payment failed page...</p>
            <script>window.location.href = 'http://localhost:3000/payment-failed';</script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html')


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def payment_cancelled(request):
    """Handle SSLCommerz payment cancelled callback"""
    try:
        print(f"=== PAYMENT CANCELLED CALLBACK ===")
        print(f"Request method: {request.method}")
        print(f"Request URL: {request.build_absolute_uri()}")
        print(f"Request data: {request.data}")
        print(f"Request query params: {request.query_params}")
        print(f"Request POST data: {request.POST}")
        print(f"Request GET data: {request.GET}")
        
        # Get order ID from SSLCommerz callback data
        order_id = None
        if request.method == 'POST':
            order_id = request.POST.get('value_a') or request.data.get('value_a')
        else:
            order_id = request.GET.get('value_a')
        
        print(f"Order ID from callback: {order_id}")
        
        if order_id:
            try:
                # Find the order and mark it as cancelled
                order = Order.objects.get(id=order_id)
                print(f"Found order: {order.id}, current status: {order.status}")
                
                # Update order to cancelled
                order.status = 'cancelled'
                order.cancelled_at = timezone.now()
                order.save()
                
                print(f"Order {order.id} marked as cancelled due to payment cancellation")
                
                # Create notification for buyer
                Notification.objects.create(
                    user=order.buyer,
                    type='payment_cancelled',
                    title='Payment Cancelled',
                    message=f'Your payment for order #{order.order_number} has been cancelled',
                    data={'order_id': str(order.id)}
                )
                
            except Order.DoesNotExist:
                print(f"Order {order_id} not found")
            except Exception as e:
                print(f"Error updating order {order_id}: {e}")
        
        # Return HTML redirect instead of Django redirect
        from django.http import HttpResponse
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta http-equiv="refresh" content="0; url=http://localhost:3000/">
        </head>
        <body>
            <p>Payment cancelled. Redirecting to homepage...</p>
            <script>window.location.href = 'http://localhost:3000/';</script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html')
    except Exception as e:
        print(f"Payment cancelled error: {e}")
        from django.http import HttpResponse
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta http-equiv="refresh" content="0; url=http://localhost:3000/">
        </head>
        <body>
            <p>Payment cancelled. Redirecting to homepage...</p>
            <script>window.location.href = 'http://localhost:3000/';</script>
        </body>
        </html>
        '''
        return HttpResponse(html_content, content_type='text/html')

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def test_payment_cancelled(request):
    """Test payment cancelled endpoint"""
    from django.http import HttpResponse
    html_content = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0; url=http://localhost:3000/">
    </head>
    <body>
        <p>Test payment cancelled. Redirecting to homepage...</p>
        <script>window.location.href = 'http://localhost:3000/';</script>
    </body>
    </html>
    '''
    return HttpResponse(html_content, content_type='text/html')

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_sslcommerz_methods(request, payment_id):
#     """Get SSLCommerz payment methods"""
#     # Temporarily disabled due to Payment model issues
#     pass

# @api_view(['POST'])
# @permission_classes([AllowAny])
# def sslcommerz_ipn(request):
#     """SSLCommerz IPN (Instant Payment Notification) handler"""
#     # Temporarily disabled due to Payment model issues
#     pass

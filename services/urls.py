from django.urls import path
from . import views

urlpatterns = [
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    
    # Services
    path('services/', views.ServiceListView.as_view(), name='service-list'),
    path('services/create/', views.ServiceCreateView.as_view(), name='service-create'),
    path('services/<uuid:id>/', views.ServiceDetailView.as_view(), name='service-detail'),
    path('services/<uuid:id>/update/', views.ServiceUpdateView.as_view(), name='service-update'),
    path('services/<uuid:id>/delete/', views.ServiceDeleteView.as_view(), name='service-delete'),
    path('services/<uuid:id>/toggle-featured/', views.toggle_featured, name='toggle-featured'),
    path('services/<uuid:service_id>/stats/', views.review_stats, name='review-stats'),
    
    # Seller services
    path('sellers/<uuid:seller_id>/services/', views.SellerServicesView.as_view(), name='seller-services'),
    
    # Reviews
    path('services/<uuid:service_id>/reviews/', views.ReviewListView.as_view(), name='review-list'),
    path('services/<uuid:service_id>/reviews/create/', views.ReviewCreateView.as_view(), name='review-create'),
    path('reviews/<uuid:id>/update/', views.ReviewUpdateView.as_view(), name='review-update'),
    path('reviews/<uuid:id>/delete/', views.ReviewDeleteView.as_view(), name='review-delete'),
    path('reviews/<uuid:review_id>/helpful/', views.ReviewHelpfulView.as_view(), name='review-helpful'),
    path('sellers/<uuid:seller_id>/reviews/', views.SellerReviewsView.as_view(), name='seller-reviews'),
    
    # Orders
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order-create'),
    path('orders/<uuid:id>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<uuid:id>/update/', views.OrderUpdateView.as_view(), name='order-update'),
    path('orders/<uuid:order_id>/messages/', views.OrderMessageListView.as_view(), name='order-messages'),
    path('orders/<uuid:order_id>/messages/create/', views.OrderMessageCreateView.as_view(), name='order-message-create'),
    path('orders/<uuid:order_id>/files/', views.OrderFileListView.as_view(), name='order-files'),
    path('orders/<uuid:order_id>/files/create/', views.OrderFileCreateView.as_view(), name='order-file-create'),
    
    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<uuid:id>/mark-read/', views.NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('notifications/mark-all-read/', views.NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),
    
    # Recommendations
    path('recommendations/', views.RecommendationListView.as_view(), name='recommendation-list'),
    path('recommendations/<uuid:id>/mark-viewed/', views.RecommendationMarkViewedView.as_view(), name='recommendation-mark-viewed'),
    path('recommendations/generate/', views.generate_recommendations, name='generate-recommendations'),
    
    # Seller Dashboard
    path('seller/earnings/', views.SellerEarningsListView.as_view(), name='seller-earnings'),
    path('seller/analytics/', views.SellerAnalyticsView.as_view(), name='seller-analytics'),
    path('seller/profile/', views.SellerProfileView.as_view(), name='seller-profile'),
    path('seller/profile/update/', views.SellerProfileUpdateView.as_view(), name='seller-profile-update'),
    path('seller/services/', views.SellerServicesManagementView.as_view(), name='seller-services-management'),
    path('seller/orders/', views.SellerOrdersManagementView.as_view(), name='seller-orders-management'),
    path('seller/reviews/', views.SellerReviewsManagementView.as_view(), name='seller-reviews-management'),
    path('seller/dashboard-stats/', views.seller_dashboard_stats, name='seller-dashboard-stats'),
    path('seller/earnings-summary/', views.seller_earnings_summary, name='seller-earnings-summary'),
    path('seller/availability/', views.update_seller_availability, name='seller-availability'),
    
    # Buyer Dashboard
    path('buyer/profile/', views.BuyerProfileView.as_view(), name='buyer-profile'),
    path('buyer/profile/update/', views.BuyerProfileUpdateView.as_view(), name='buyer-profile-update'),
    path('buyer/saved-services/', views.SavedServiceListView.as_view(), name='saved-services'),
    path('buyer/saved-services/create/', views.SavedServiceCreateView.as_view(), name='saved-service-create'),
    path('buyer/saved-services/<int:id>/delete/', views.SavedServiceDeleteView.as_view(), name='saved-service-delete'),
    path('buyer/analytics/', views.BuyerAnalyticsView.as_view(), name='buyer-analytics'),
    path('buyer/preferences/', views.BuyerPreferencesView.as_view(), name='buyer-preferences'),
    path('buyer/preferences/update/', views.BuyerPreferencesUpdateView.as_view(), name='buyer-preferences-update'),
    path('buyer/order-history/', views.BuyerOrderHistoryView.as_view(), name='buyer-order-history'),
    path('buyer/review-history/', views.BuyerReviewHistoryView.as_view(), name='buyer-review-history'),
    path('buyer/dashboard-stats/', views.buyer_dashboard_stats, name='buyer-dashboard-stats'),
    path('buyer/dashboard-stats-fresh/', views.buyer_dashboard_stats_fresh, name='buyer-dashboard-stats-fresh'),
    path('buyer/spending-summary/', views.buyer_spending_summary, name='buyer-spending-summary'),
    path('buyer/toggle-save/', views.toggle_service_save, name='toggle-service-save'),
    path('buyer/activity-timeline/', views.buyer_activity_timeline, name='buyer-activity-timeline'),
    
    # Test endpoints
    path('test-simple/', views.test_simple_endpoint, name='test-simple'),
    path('test-cors/', views.test_cors_endpoint, name='test-cors'),
    path('test-simple/', views.test_simple_endpoint, name='test-simple'),
    
    # Statistics
    path('stats/', views.service_stats, name='service-stats'),
    path('order-stats/', views.order_stats, name='order-stats'),
    
    # Payment URLs
    path('payments/', views.PaymentListView.as_view(), name='payment-list'),
    path('payments/<uuid:id>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    path('payments/methods/', views.PaymentMethodListView.as_view(), name='payment-method-list'),
    path('payments/initiate/<uuid:order_id>/', views.initiate_payment, name='initiate-payment'),
    path('payments/<uuid:payment_id>/methods/', views.get_sslcommerz_methods, name='sslcommerz-methods'),
    path('payments/sslcommerz/ipn/', views.sslcommerz_ipn, name='sslcommerz-ipn'),
    path('payments/success/', views.payment_success, name='payment-success'),
    path('payments/failed/', views.payment_failed, name='payment-failed'),
    path('payments/cancelled/', views.payment_cancelled, name='payment-cancelled'),
]

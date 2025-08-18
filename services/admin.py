from django.contrib import admin
from .models import Category, Service, ServiceImage, Review, ReviewImage, ReviewHelpful, Order, OrderMessage, OrderFile, Notification, Recommendation, SellerEarnings, SellerAnalytics, SellerProfile, BuyerProfile, SavedService, BuyerAnalytics, BuyerPreferences

class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 1

class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 1

class ReviewHelpfulInline(admin.TabularInline):
    model = ReviewHelpful
    extra = 0
    readonly_fields = ['created_at']

class OrderMessageInline(admin.TabularInline):
    model = OrderMessage
    extra = 0
    readonly_fields = ['created_at']

class OrderFileInline(admin.TabularInline):
    model = OrderFile
    extra = 0
    readonly_fields = ['created_at']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'service_count', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def service_count(self, obj):
        return obj.services.filter(is_active=True).count()
    service_count.short_description = 'Active Services'

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['title', 'seller', 'category', 'price', 'delivery_time', 'average_rating', 'total_reviews', 'is_active', 'is_featured', 'created_at']
    list_filter = ['category', 'is_active', 'is_featured', 'created_at']
    search_fields = ['title', 'description', 'seller__email', 'seller__first_name', 'seller__last_name']
    list_editable = ['is_active', 'is_featured']
    readonly_fields = ['average_rating', 'total_reviews', 'created_at', 'updated_at']
    inlines = [ServiceImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'seller', 'category')
        }),
        ('Pricing & Delivery', {
            'fields': ('price', 'delivery_time', 'requirements')
        }),
        ('Service Details', {
            'fields': ('features', 'images')
        }),
        ('Status & Visibility', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Ratings', {
            'fields': ('average_rating', 'total_reviews'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('seller', 'category')

@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
    list_display = ['service', 'image_url', 'is_primary', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['service__title', 'caption']
    list_editable = ['is_primary']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['service', 'buyer', 'seller', 'rating', 'title', 'is_verified', 'is_helpful', 'created_at']
    list_filter = ['rating', 'is_verified', 'created_at']
    search_fields = ['service__title', 'buyer__email', 'seller__email', 'title', 'comment']
    list_editable = ['is_verified']
    readonly_fields = ['is_helpful', 'created_at', 'updated_at']
    inlines = [ReviewImageInline, ReviewHelpfulInline]
    
    fieldsets = (
        ('Review Information', {
            'fields': ('service', 'buyer', 'seller', 'rating', 'title', 'comment')
        }),
        ('Status', {
            'fields': ('is_verified', 'is_helpful')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('service', 'buyer', 'seller')

@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ['review', 'image_url', 'caption', 'created_at']
    list_filter = ['created_at']
    search_fields = ['review__title', 'caption']
    readonly_fields = ['created_at']

@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ['review', 'user', 'is_helpful', 'created_at']
    list_filter = ['is_helpful', 'created_at']
    search_fields = ['review__title', 'user__email']
    readonly_fields = ['created_at']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'service', 'buyer', 'seller', 'status', 'total_amount', 'is_paid', 'placed_at']
    list_filter = ['status', 'is_paid', 'placed_at']
    search_fields = ['order_number', 'service__title', 'buyer__email', 'seller__email']
    list_editable = ['status', 'is_paid']
    readonly_fields = ['order_number', 'placed_at', 'confirmed_at', 'started_at', 'completed_at', 'cancelled_at']
    inlines = [OrderMessageInline, OrderFileInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'service', 'buyer', 'seller', 'status', 'total_amount')
        }),
        ('Requirements', {
            'fields': ('requirements', 'special_instructions')
        }),
        ('Delivery', {
            'fields': ('expected_delivery_date', 'actual_delivery_date')
        }),
        ('Notes', {
            'fields': ('buyer_notes', 'seller_notes')
        }),
        ('Payment', {
            'fields': ('is_paid', 'payment_method')
        }),
        ('Timestamps', {
            'fields': ('placed_at', 'confirmed_at', 'started_at', 'completed_at', 'cancelled_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('service', 'buyer', 'seller')

@admin.register(OrderMessage)
class OrderMessageAdmin(admin.ModelAdmin):
    list_display = ['order', 'sender', 'message_preview', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['order__order_number', 'sender__email', 'message']
    readonly_fields = ['created_at']
    
    def message_preview(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'

@admin.register(OrderFile)
class OrderFileAdmin(admin.ModelAdmin):
    list_display = ['order', 'file_name', 'file_type', 'uploaded_by', 'file_size', 'created_at']
    list_filter = ['file_type', 'created_at']
    search_fields = ['order__order_number', 'file_name', 'uploaded_by__email']
    readonly_fields = ['created_at']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'title', 'is_read', 'is_email_sent', 'created_at']
    list_filter = ['notification_type', 'is_read', 'is_email_sent', 'created_at']
    search_fields = ['recipient__email', 'title', 'message']
    list_editable = ['is_read', 'is_email_sent']
    readonly_fields = ['created_at', 'read_at']
    
    fieldsets = (
        ('Notification Information', {
            'fields': ('recipient', 'notification_type', 'title', 'message')
        }),
        ('Status', {
            'fields': ('is_read', 'is_email_sent')
        }),
        ('Related Objects', {
            'fields': ('order', 'service', 'review'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'read_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'service', 'score', 'reason', 'is_viewed', 'created_at']
    list_filter = ['is_viewed', 'created_at']
    search_fields = ['user__email', 'service__title', 'reason']
    list_editable = ['is_viewed']
    readonly_fields = ['created_at']

# Seller Dashboard Admin
@admin.register(SellerEarnings)
class SellerEarningsAdmin(admin.ModelAdmin):
    list_display = ['seller', 'order_number', 'gross_amount', 'platform_fee', 'net_amount', 'is_paid_out', 'created_at']
    list_filter = ['is_paid_out', 'created_at']
    search_fields = ['seller__email', 'order__order_number']
    list_editable = ['is_paid_out']
    readonly_fields = ['gross_amount', 'platform_fee', 'net_amount', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Earnings Information', {
            'fields': ('seller', 'order', 'gross_amount', 'platform_fee', 'net_amount')
        }),
        ('Payment Status', {
            'fields': ('is_paid_out', 'paid_out_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Order Number'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('seller', 'order', 'order__service')

@admin.register(SellerAnalytics)
class SellerAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['seller', 'total_services', 'total_orders', 'completed_orders', 'average_rating', 'total_earnings', 'last_updated']
    search_fields = ['seller__email', 'seller__first_name', 'seller__last_name']
    readonly_fields = [
        'total_services', 'active_services', 'featured_services', 'total_orders', 'completed_orders',
        'cancelled_orders', 'average_order_value', 'total_reviews', 'average_rating', 'five_star_reviews',
        'four_star_reviews', 'three_star_reviews', 'two_star_reviews', 'one_star_reviews',
        'total_earnings', 'total_platform_fees', 'net_earnings', 'paid_out_earnings', 'pending_earnings',
        'orders_this_month', 'earnings_this_month', 'orders_this_year', 'earnings_this_year', 'last_updated'
    ]
    
    fieldsets = (
        ('Service Metrics', {
            'fields': ('total_services', 'active_services', 'featured_services')
        }),
        ('Order Metrics', {
            'fields': ('total_orders', 'completed_orders', 'cancelled_orders', 'average_order_value')
        }),
        ('Review Metrics', {
            'fields': ('total_reviews', 'average_rating', 'five_star_reviews', 'four_star_reviews', 
                      'three_star_reviews', 'two_star_reviews', 'one_star_reviews')
        }),
        ('Financial Metrics', {
            'fields': ('total_earnings', 'total_platform_fees', 'net_earnings', 
                      'paid_out_earnings', 'pending_earnings')
        }),
        ('Time-based Metrics', {
            'fields': ('orders_this_month', 'earnings_this_month', 'orders_this_year', 'earnings_this_year')
        }),
        ('Timestamps', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('seller')

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ['seller', 'business_name', 'experience_years', 'completion_rate', 'on_time_delivery_rate', 'is_available', 'created_at']
    list_filter = ['is_available', 'experience_years', 'created_at']
    search_fields = ['seller__email', 'business_name', 'business_description']
    list_editable = ['is_available']
    readonly_fields = ['completion_rate', 'on_time_delivery_rate', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Business Information', {
            'fields': ('business_name', 'business_description', 'business_website', 'business_phone', 'business_address')
        }),
        ('Professional Information', {
            'fields': ('skills', 'experience_years', 'education', 'certifications')
        }),
        ('Social Media & Portfolio', {
            'fields': ('portfolio_url', 'linkedin_url', 'github_url', 'behance_url')
        }),
        ('Business Settings', {
            'fields': ('response_time', 'completion_rate', 'on_time_delivery_rate')
        }),
        ('Availability', {
            'fields': ('is_available', 'max_orders_per_month', 'current_month_orders')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('seller')

# Buyer Dashboard Admin
@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ['buyer', 'company_name', 'job_title', 'industry', 'preferred_contact_method', 'is_active', 'created_at']
    list_filter = ['is_active', 'preferred_contact_method', 'created_at']
    search_fields = ['buyer__email', 'buyer__first_name', 'buyer__last_name', 'company_name', 'job_title']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('company_name', 'job_title', 'industry', 'company_size')
        }),
        ('Preferences', {
            'fields': ('preferred_categories', 'budget_range', 'preferred_delivery_time')
        }),
        ('Communication', {
            'fields': ('preferred_contact_method', 'notification_preferences')
        }),
        ('Account Settings', {
            'fields': ('is_active', 'auto_save_services', 'show_recommendations')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('buyer')

@admin.register(SavedService)
class SavedServiceAdmin(admin.ModelAdmin):
    list_display = ['buyer', 'service', 'saved_at', 'notes_preview']
    list_filter = ['saved_at']
    search_fields = ['buyer__email', 'service__title', 'notes']
    readonly_fields = ['saved_at']
    
    def notes_preview(self, obj):
        return obj.notes[:100] + '...' if len(obj.notes) > 100 else obj.notes
    notes_preview.short_description = 'Notes'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('buyer', 'service', 'service__seller')

@admin.register(BuyerAnalytics)
class BuyerAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['buyer', 'total_orders', 'completed_orders', 'total_spent', 'average_order_value', 'total_reviews_given', 'last_updated']
    search_fields = ['buyer__email', 'buyer__first_name', 'buyer__last_name']
    readonly_fields = [
        'total_orders', 'completed_orders', 'cancelled_orders', 'total_spent', 'average_order_value',
        'total_reviews_given', 'average_rating_given', 'total_services_viewed', 'total_services_saved',
        'favorite_categories', 'orders_this_month', 'spent_this_month', 'orders_this_year', 'spent_this_year',
        'last_order_date', 'last_review_date', 'last_login_date', 'last_updated'
    ]
    
    fieldsets = (
        ('Order Statistics', {
            'fields': ('total_orders', 'completed_orders', 'cancelled_orders', 'total_spent', 'average_order_value')
        }),
        ('Review Statistics', {
            'fields': ('total_reviews_given', 'average_rating_given')
        }),
        ('Service Interaction', {
            'fields': ('total_services_viewed', 'total_services_saved', 'favorite_categories')
        }),
        ('Time-based Statistics', {
            'fields': ('orders_this_month', 'spent_this_month', 'orders_this_year', 'spent_this_year')
        }),
        ('Activity Dates', {
            'fields': ('last_order_date', 'last_review_date', 'last_login_date')
        }),
        ('Timestamps', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('buyer')

@admin.register(BuyerPreferences)
class BuyerPreferencesAdmin(admin.ModelAdmin):
    list_display = ['buyer', 'preferred_seller_level', 'preferred_rating', 'preferred_currency', 'profile_visibility', 'created_at']
    list_filter = ['preferred_seller_level', 'preferred_currency', 'profile_visibility', 'created_at']
    search_fields = ['buyer__email', 'buyer__first_name', 'buyer__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Service Preferences', {
            'fields': ('preferred_service_types', 'preferred_seller_level', 'preferred_rating')
        }),
        ('Budget Preferences', {
            'fields': ('min_budget', 'max_budget', 'preferred_currency')
        }),
        ('Communication Preferences', {
            'fields': ('language_preference', 'timezone', 'response_time_preference')
        }),
        ('Notification Settings', {
            'fields': ('email_notifications', 'order_updates', 'new_services', 'recommendations', 'marketing_emails')
        }),
        ('Privacy Settings', {
            'fields': ('profile_visibility', 'show_order_history', 'show_reviews')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('buyer')

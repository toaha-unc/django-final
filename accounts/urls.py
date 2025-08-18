from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.login, name='login'),
    path('auth/register/', views.register, name='register'),
    path('auth/verify-email/<uuid:token>/', views.verify_email, name='verify-email'),
    path('auth/resend-verification/', views.resend_verification_email, name='resend-verification'),
    path('auth/create-test-users/', views.create_test_users, name='create-test-users'),
    path('auth/test-users-status/', views.test_users_status, name='test-users-status'),
    path('auth/test-jwt/', views.test_jwt_token, name='test-jwt'),
    path('auth/cleanup-users/', views.cleanup_users, name='cleanup-users'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('logout/', views.logout_view, name='logout'),
]

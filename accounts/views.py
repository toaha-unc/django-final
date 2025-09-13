from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid

from .models import User, UserProfile
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserProfileSerializer,
    UserSerializer
)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Send email verification
        try:
            send_verification_email(user)
            return Response({
                'message': 'User registered successfully. Please check your email for verification.',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            # If email sending fails, still create the user but inform about the issue
            return Response({
                'message': 'User registered successfully but email verification could not be sent.',
                'user_id': user.id,
                'error': str(e)
            }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        logout(request)
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request, token):
    try:
        user = get_object_or_404(User, email_verification_token=token)
        
        # Check if token is expired (24 hours)
        if user.email_verification_sent_at:
            expiration_time = user.email_verification_sent_at + timedelta(hours=24)
            if timezone.now() > expiration_time:
                return Response({
                    'error': 'Verification link has expired. Please request a new one.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_email_verified = True
        user.email_verification_token = uuid.uuid4()  # Generate new token
        user.save()
        
        return Response({
            'message': 'Email verified successfully. You can now log in.'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'error': 'Invalid verification token.'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_email(request):
    email = request.data.get('email')
    if not email:
        return Response({
            'error': 'Email is required.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
        if user.is_email_verified:
            return Response({
                'error': 'Email is already verified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate new verification token
        user.email_verification_token = uuid.uuid4()
        user.email_verification_sent_at = timezone.now()
        user.save()
        
        send_verification_email(user)
        
        return Response({
            'message': 'Verification email sent successfully.'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'error': 'User with this email does not exist.'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_test_users(request):
    """Create test users for development/testing purposes"""
    try:
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
        else:
            admin_user.set_password('admin123')
            admin_user.is_email_verified = True
            admin_user.save()

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
        else:
            seller_user.set_password('seller123')
            seller_user.is_email_verified = True
            seller_user.save()

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
        else:
            buyer_user.set_password('buyer123')
            buyer_user.is_email_verified = True
            buyer_user.save()

        return Response({
            'message': 'Test users created/updated successfully!',
            'users': {
                'admin': 'admin@gmail.com / admin123',
                'seller': 'supabase_seller@example.com / seller123',
                'buyer': 'supabase_buyer@example.com / buyer123'
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to create test users: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def test_users_status(request):
    """Check the status of test users"""
    try:
        users_data = {}
        
        # Check admin user
        try:
            admin_user = User.objects.get(email='admin@gmail.com')
            users_data['admin'] = {
                'exists': True,
                'email': admin_user.email,
                'verified': admin_user.is_email_verified,
                'password_check': admin_user.check_password('admin123')
            }
        except User.DoesNotExist:
            users_data['admin'] = {'exists': False}
        
        # Check seller user
        try:
            seller_user = User.objects.get(email='supabase_seller@example.com')
            users_data['seller'] = {
                'exists': True,
                'email': seller_user.email,
                'verified': seller_user.is_email_verified,
                'password_check': seller_user.check_password('seller123')
            }
        except User.DoesNotExist:
            users_data['seller'] = {'exists': False}
        
        # Check buyer user
        try:
            buyer_user = User.objects.get(email='supabase_buyer@example.com')
            users_data['buyer'] = {
                'exists': True,
                'email': buyer_user.email,
                'verified': buyer_user.is_email_verified,
                'password_check': buyer_user.check_password('buyer123')
            }
        except User.DoesNotExist:
            users_data['buyer'] = {'exists': False}
        
        return Response({
            'message': 'Test users status',
            'users': users_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to check test users: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def test_jwt_token(request):
    """Test JWT token generation"""
    try:
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'error': 'Email and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                if not user.is_email_verified:
                    return Response({
                        'error': 'Please verify your email before logging in'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Test JWT token generation
                refresh = RefreshToken()
                refresh['user_id'] = str(user.id)  # Convert UUID to string
                refresh['email'] = user.email
                refresh['role'] = user.role
                
                return Response({
                    'message': 'JWT token generation successful',
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'role': user.role,
                        'verified': user.is_email_verified
                    },
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid credentials'
                }, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'error': f'Failed to generate JWT token: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return self.request.user.profile

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout and blacklist refresh token"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        logout(request)
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def cleanup_users(request):
    """
    Clean up users to keep only the 3 specified test users
    Admin only endpoint
    """
    # Define the users we want to keep
    keep_users = [
        'admin@gmail.com',
        'supabase_seller@example.com',
        'supabase_buyer@example.com'
    ]
    
    # Get all users
    all_users = User.objects.all()
    total_users = all_users.count()
    
    # Count users to be deleted
    users_to_delete = all_users.exclude(email__in=keep_users)
    delete_count = users_to_delete.count()
    
    if delete_count == 0:
        return Response({
            'message': 'No users to delete. All specified users are already present.',
            'total_users': total_users,
            'deleted_count': 0
        })
    
    # Get list of users to be deleted
    users_to_delete_list = [
        {
            'id': str(user.id),
            'email': user.email,
            'role': user.role
        }
        for user in users_to_delete
    ]
    
    # Delete unwanted users
    deleted_count = users_to_delete.delete()[0]
    
    # Get remaining users
    remaining_users = User.objects.all()
    remaining_users_list = [
        {
            'id': str(user.id),
            'email': user.email,
            'role': user.role,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser
        }
        for user in remaining_users
    ]
    
    return Response({
        'message': f'Successfully deleted {deleted_count} users',
        'total_users_before': total_users,
        'deleted_count': deleted_count,
        'remaining_users_count': remaining_users.count(),
        'users_deleted': users_to_delete_list,
        'remaining_users': remaining_users_list
    }, status=status.HTTP_200_OK)

def send_verification_email(user):
    """Send email verification to user"""
    subject = 'Verify your email address'
    message = f"""
    Hello {user.first_name or user.email},
    
    Please verify your email address by clicking the link below:
    
    https://django-final-delta.vercel.app/api/auth/verify-email/{user.email_verification_token}/
    
    This link will expire in 24 hours.
    
    If you didn't create an account, please ignore this email.
    
    Best regards,
    Freelancer Platform Team
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

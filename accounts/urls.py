from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('logout/', views.logout_view, name='logout'),
]

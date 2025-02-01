from django.urls import path
from . import views

urlpatterns = [
    path('admin_signup/', views.admin_sign_in, name='admin_sign_in'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('contents/', views.contents, name='contents'),
    path('settings/', views.settings, name='settings'),
    path('admin_logout/', views.admin_logout, name='admin_logout'),
    path('coupon/',views.coupon,name='coupon'),
    
] 

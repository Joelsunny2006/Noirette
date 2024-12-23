from django.urls import path
from . import views

urlpatterns = [
    # Admin URLs
    path('admin/coupons/', views.coupon_list, name='coupon_list'),
    path('admin/coupons/create/', views.create_coupon, name='create_coupon'),
    path('admin/coupons/edit/<int:coupon_id>/', views.edit_coupon, name='edit_coupon'),
    path('admin/coupons/delete/<int:coupon_id>/', views.delete_coupon, name='delete_coupon'),
    
    # Customer URLs
    path('coupon/apply/', views.apply_coupon, name='apply_coupon'),
    path('coupon/remove/', views.remove_coupon, name='remove_coupon'),
]
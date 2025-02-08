from django.urls import path
from . import views


urlpatterns = [
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('cart/checkout/', views.checkout_view, name='checkout'),
    path('update-quantity/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('add-address/', views.add_address_view, name='add_address'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:variant_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:variant_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),  
    path('wishlist/status/<int:variant_id>/', views.check_wishlist_status, name='check_wishlist_status'),
    # path('checkout/<str:serial_number>/', views.checkout_view, name='checkout'),


]

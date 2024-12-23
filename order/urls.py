from django.urls import path
from . import views

app_name = 'order'

urlpatterns = [ 
    path('addresses/', views.address_list, name='address_list'),  
    path('addresses/save/', views.save_address, name='save_address'),  
    path('addresses/<int:address_id>/delete/', views.delete_address, name='delete_address'),  
    path('addresses/<int:address_id>/edit/', views.edit_address, name='edit_address'),
    path('orders/', views.orders, name='orders'),
    path('update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('delete-address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('razorpay_payment/',views.razorpay_payment,name='razorpay_payment'),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('order/<int:order_id>/return/', views.return_order, name='return_order'),
    path("continue_payment/<int:order_id>/", views.continue_payment, name="continue_payment"),
    path('order/<int:order_id>/download-invoice/', views.download_invoice, name='download_invoice'),
    path('place-order/', views.place_order, name='place_order'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('order-success/', views.order_success, name='order_success'),
    path('order-failure/', views.order_failure, name='order_failure'),
]
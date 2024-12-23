# urls.py
from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
urlpatterns = [
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/create-order/', views.create_wallet_razorpay_order, name='create_wallet_razorpay_order'),
    path('wallet/payment-success/', views.wallet_payment_success, name='wallet_payment_success'),
    path('process_wallet_refund/', views.process_wallet_refund, name='process_wallet_refund'),

]
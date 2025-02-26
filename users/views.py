import random
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect ,reverse
from django.contrib.auth import login, authenticate
from django.contrib import messages
from .forms import SignUpForm, LoginForm, OTPForm  
from .models import UserProfile, OTP
from django.utils import timezone
from datetime import timedelta
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from category.models import Category
from product.models import *
from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Value
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from order.models import *
from cart.models import *
from wallet.models import *
from django.http import HttpResponseRedirect
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.cache import cache_control, never_cache
from django.http import JsonResponse
from django.db.models import Subquery, OuterRef, Q
from django.db.models import Sum

def send_otp_email(user, otp_code):
    subject = "Your OTP Code"
    message = f"Your OTP code is: {otp_code}"
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]
    
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)

def generate_otp(user):
    otp_code = str(random.randint(100000, 999999))
    OTP.objects.create(user=user, otp_code=otp_code, is_verified=False)
    send_otp_email(user, otp_code)  # Send the OTP email
    print(otp_code)
    return otp_code


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            
            generate_otp(user)

            # Clear previous error messages before adding success message
            storage = messages.get_messages(request)
            storage.used = True  # This clears the previous messages
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': "Account created successfully! Please verify your email with the OTP.",
                    'redirect': reverse('verify_otp', args=[user.id])
                })

            messages.success(request, "Account created successfully! Please verify your email with the OTP.")
            return redirect('verify_otp', user.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, error_list in form.errors.items():
                    errors[field] = [str(error) for error in error_list]
                return JsonResponse({
                    'status': 'error',
                    'errors': errors
                })
            
            # Password mismatch check
            password = request.POST.get('password', '')
            confirm_password = request.POST.get('confirm_password', '')
            if password != confirm_password:
                messages.error(request, "Your confirm password does not match the password.")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
    else:
        form = SignUpForm()
    
    return render(request, "user_side/signup.html", {'form': form})


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def verify_otp(request, user_id):
    user = get_object_or_404(UserProfile, id=user_id)
    
    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            
            try:
                otp = OTP.objects.get(user=user, otp_code=otp_code, is_verified=False)
                
                if otp.is_expired():
                    messages.error(request, "OTP has expired. Please request a new one.")
                    return redirect('resend_otp', user_id)

                # Mark the OTP as verified
                otp.is_verified = True
                otp.save()

                # Activate the user and log them in
                user.is_active = True
                user.save()

                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                messages.success(request, "OTP verified successfully.")
                return redirect('home')
            except OTP.DoesNotExist:
                messages.error(request, "Invalid OTP. Please try again.")
                return redirect('verify_otp', user.id)
    else:
        form = OTPForm()
    return render(request, 'user_side/verify_otp.html', {'form': form, 'user_id': user_id})


def resend_otp(request, user_id):
    try:
        # Get the user from the database
        user = get_object_or_404(UserProfile, id=user_id)
        generate_otp(user)  # Send the OTP to the user
        
        messages.success(request, "A new OTP has been sent to your email.")
        return redirect('verify_otp', user_id=user.id)
    
    except Exception as e:
        # Handle unexpected errors gracefully
        messages.error(request, "Something went wrong. Please try again.")
        return redirect('login') 

import logging
logger = logging.getLogger(__name__)

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            user = form.cleaned_data.get('user')
            login(request, user)
            
            messages.success(request, "Login successful! Welcome back.")
            return redirect('home')
        else:
            error_messages = form.get_error_messages()
            for error in error_messages:
                messages.error(request, error)
    else:
        form = LoginForm()
    return render(request, "user_side/login.html", {'form': form})


from django.db.models import Count

def home(request):
    if not request.user.is_authenticated:
        request.session.flush()

    # Fetch the best-selling product based on order count
    best_selling_product = (
        Product.objects.annotate(order_count=Count('variants__orderitem'))
        .filter(is_deleted=False)
        .order_by('-order_count')
        .first()
    )

    # Fetch only the first 3 products
    products = Product.objects.filter(is_deleted=False).order_by('serial_number')[:3]

    # Attach the first image URL to each product
    for product in products:
        first_image = product.images.first()
        product.first_image_url = first_image.image_url.url if first_image else '/media/default_image.jpg'

    # Fetch cart, wishlist, and wallet data
    cart_count = wishlist_count = wallet_balance = 0

    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).first()
        wishlist_count = Wishlist.objects.filter(user=request.user).first()
        wallet_balance = Wallet.objects.filter(user=request.user).first()

        cart_count = cart_count.items.aggregate(total=Count('quantity'))['total'] if cart_count else 0
        wishlist_count = wishlist_count.items.count() if wishlist_count else 0
        wallet_balance = wallet_balance.balance if wallet_balance else 0

    return render(request, 'user_side/home.html', {
        "products": products,  # Only first 3 products
        "best_selling_product": best_selling_product,
        "cart_count": cart_count,
        "wishlist_count": wishlist_count,
        "wallet_balance": wallet_balance,
    })

from django.db.models import F, ExpressionWrapper, FloatField, Subquery, OuterRef, Q
from django.core.paginator import Paginator

def shop(request):
    # Subquery to calculate the minimum discounted price for each product
    min_discount_price = Subquery(
        Variant.objects.filter(product=OuterRef('pk')).annotate(
            calculated_discount_price=ExpressionWrapper(
                F('variant_price') - (F('variant_price') * F('product__offer_percentage') / 100),
                output_field=FloatField()
            )
        ).order_by('calculated_discount_price').values('calculated_discount_price')[:1]
    )

    # Fetch active categories and brands
    categories = Category.objects.filter(status=True, is_deleted=False)  
    brands = Brand.objects.filter(status='active')

    # Filter products ensuring they belong to active categories and brands
    products = Product.objects.filter(
        is_deleted=False, 
        category__status=True, category__is_deleted=False,  # Ensure category is active and not deleted
        brand__status="active"  # Ensure brand is active
    ).prefetch_related('variants').annotate(
        min_discount_price=min_discount_price
    ).distinct()

    # Get all filter parameters
    search_query = request.GET.get('q', '')
    selected_categories = request.GET.getlist('categories')
    selected_brands = request.GET.getlist('brands')
    sort_by = request.GET.get('sort', 'default')

    # Apply search filter
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # Filter by selected brands (ensure they are active)
    if selected_brands:
        products = products.filter(brand__name__in=selected_brands, brand__status="active")

    # Filter by selected categories (ensure they are active and not deleted)
    if selected_categories:
        products = products.filter(category__slug__in=selected_categories, category__status=True, category__is_deleted=False)

    # Get price filter parameters with proper defaults
    try:
        price_from = max(1, float(request.GET.get('price_from', '1')))
    except ValueError:
        price_from = 1

    try:
        price_to = min(1000, float(request.GET.get('price_to', '1000')))
    except ValueError:
        price_to = 1000

    # Ensure price_to is not less than price_from
    if price_to < price_from:
        price_to = price_from

    # Apply price range filter
    products = products.filter(
        min_discount_price__gte=price_from,
        min_discount_price__lte=price_to
    )

    # Apply sorting
    if sort_by == 'price_low_to_high':
        products = products.order_by('min_discount_price')
    elif sort_by == 'price_high_to_low':
        products = products.order_by('-min_discount_price')
    elif sort_by == 'new_arrivals':
        products = products.order_by('-created')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')

    # Ensure queryset is distinct
    products = products.distinct()

    # Pagination
    products_per_page = 6
    paginator = Paginator(products, products_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Set First Image for Products
    for product in page_obj:
        first_image = product.images.first()
        product.first_image_url = (
            first_image.image_url.url if first_image and hasattr(first_image, 'image_url') else '/static/default.jpg'
        )

    # Sort options
    sort_options = [
        ('default', 'Default Sorting'),
        ('price_low_to_high', 'Price: Low to High'),
        ('price_high_to_low', 'Price: High to Low'),
        ('new_arrivals', 'New Arrivals'),
        ('name_asc', 'Name: A-Z'),
        ('name_desc', 'Name: Z-A')
    ]

    # Get cart count
    cart_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart_count = cart.items.aggregate(total=models.Sum('quantity'))['total'] or 0
        except Cart.DoesNotExist:
            cart_count = 0
        
    wishlist_count = 0
    wallet_balance = 0

    if request.user.is_authenticated:
        # Get Wishlist Count
        try:
            wishlist = Wishlist.objects.filter(user=request.user).first()
            if wishlist:
                wishlist_count = wishlist.items.count()
        except Wishlist.DoesNotExist:
            wishlist_count = 0

        # Get Wallet Balance
        try:
            wallet = Wallet.objects.filter(user=request.user).first()
            if wallet:
                wallet_balance = wallet.balance
        except Wallet.DoesNotExist:
            wallet_balance = 0

    # Create context with all parameters
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'cart_count': cart_count,
        'brands': brands,
        'sort_options': sort_options,
        'current_sort': sort_by,
        'current_price_from': int(price_from) if price_from.is_integer() else price_from,
        'current_price_to': int(price_to) if price_to.is_integer() else price_to,
        'selected_categories': selected_categories,
        'selected_brands': selected_brands,
        'search_query': search_query,
        'wishlist_count': wishlist_count,
        'wallet_balance': wallet_balance
    }

    return render(request, 'user_side/shop.html', context)

def checkout(request):
    return render(request, 'user_side/checkout.html')

def about(request):
    return render(request, 'user_side/about.html')

def contact(request):
    return render(request, 'user_side/contact.html')

@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def logout_view(request):
    # Clear session data
    request.session.flush()
    
    # Log out the user
    logout(request)
    
    # Create response with cache-control headers
    response = redirect('home')
    
    # Clear all authentication-related cookies
    response.delete_cookie('sessionid')
    response.delete_cookie('csrftoken')
    
    # Add cache-control headers
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response

def support(request):
    cart_count = 0
    wishlist_count = 0  # ✅ Initialize to avoid UnboundLocalError
    wallet_balance = 0  

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart_count = cart.items.aggregate(total=models.Sum('quantity'))['total'] or 0
        except Cart.DoesNotExist:
            cart_count = 0

        try:
            wishlist = Wishlist.objects.filter(user=request.user).first()
            if wishlist:
                wishlist_count = wishlist.items.count()
        except Wishlist.DoesNotExist:
            wishlist_count = 0

        try:
            wallet = Wallet.objects.filter(user=request.user).first()
            if wallet:
                wallet_balance = wallet.balance
        except Wallet.DoesNotExist:
            wallet_balance = 0

    context = {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'wallet_balance': wallet_balance,
    }

    return render(request, 'user_side/support.html', context)


@login_required
def user_profile(request):

    # Fetch user's addresses and orders (you'll need to implement these queries)
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'user_side/user_profile.html', {
        'addresses': addresses,
        'orders': orders,
        "user": request.user
    })

@login_required
def edit_profile(request):
    """
    Handle profile editing directly in the modal
    """
    if request.method == 'POST':
        user = request.user
        username = request.POST.get('username')
        email = request.POST.get('email')
        
        # Validate inputs
        if not username or not email:
            messages.error(request, 'Username and email are required.')
            return redirect('user_profile')
        
        # Check if email is already in use by another user
        if UserProfile.objects.exclude(pk=user.pk).filter(email=email).exists():
            messages.error(request, 'This email is already in use.')
            return redirect('user_profile')
        
        # Update user details
        user.username = username
        user.email = email
        user.save()
        
        messages.success(request, 'Profile updated successfully.')
        return redirect('user_profile')
    
    return redirect('user_profile')

@login_required
def change_password(request):
    """
    Handle password change directly in the modal
    """
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate inputs
        if not current_password or not new_password or not confirm_password:
            messages.error(request, 'All password fields are required.')
            return redirect('user_profile')
        
        # Check if current password is correct
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('user_profile')
        
        # Check if new passwords match
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('user_profile')
        
        # Check password strength (basic example)
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('user_profile')
        
        # Set and save new password
        request.user.set_password(new_password)
        request.user.save()
        
        # Update session to keep user logged in
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Password changed successfully.')
        return redirect('user_profile')
    
    return redirect('user_profile')


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = UserProfile.objects.get(email=email)
            # Generate a unique password reset link
            reset_link = f"https://noirette.shop/reset-password/{user.id}/"
            # Send the email
            send_mail(
                subject="Password Reset Request",
                message=f"Click the link to reset your password: {reset_link}",
                from_email="joelsunnyp@gmail.com",
                recipient_list=[email],
            )
            messages.success(request, "Password reset email sent!")
        except UserProfile.DoesNotExist:
            messages.error(request, "No user found with this email.")
        return HttpResponseRedirect('/forgot-password/')
    return render(request, 'user_side/forgot-password.html')


def reset_password(request, user_id):
    if request.method == "POST":
        new_password = request.POST.get("password")
        user = UserProfile.objects.get(id=user_id)
        user.set_password(new_password)
        user.save()
        messages.success(request, "Password reset successfully!")
        return HttpResponseRedirect('/login/')
    return render(request, 'user_side/reset-password.html', {"user_id": user_id})
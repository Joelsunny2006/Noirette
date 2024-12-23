from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.views.decorators.cache import cache_control
from users.models import UserProfile
from category.models import Category
from product.models import Product
from django.contrib.auth.models import User 
from django.shortcuts import redirect, get_object_or_404
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import cloudinary.uploader
from django.contrib import messages
from order.models import *
def admin_sign_in(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)

        if user is not None:
            if  user.is_admin:
                login(request, user)
                messages.success(request, 'Successfully logged in as admin!')
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'You are not an admin.')
        else:
            messages.error(request, 'Invalid credentials.')
    return render(request, 'admin_side/admin_sign_in.html')

def products_view(request):
    products = Product.objects.filter(is_deleted=False).order_by('serial_number')
    categories = Category.objects.filter(is_deleted=False)

    return render(request, 'admin_side/products.html', {'products': products,'categories': categories})

# Add a new product
def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('productName')
        price = float(request.POST.get('productPrice'))
        description = request.POST.get('productDescription')
        category_id = request.POST.get('category')
        stock = int(request.POST.get('productStock'))

        try:
            category = Category.objects.get(id=category_id, is_deleted=False)
        except Category.DoesNotExist:
            messages.error(request, "Invalid category selected.")
            categories = Category.objects.filter(is_deleted=False)
            return render(request, 'admin_side/add_product.html', {'categories': categories})

        product = Product.objects.create(
            name=name,
            price=price,
            description=description,
            category=category,
            stock=stock,
        )

        product_images = request.FILES.getlist('product_images')
        image_paths = []
        for image in product_images:
            upload_result = cloudinary.uploader.upload(image)
            
            image_paths.append(upload_result)

        product.images = image_paths
        product.save()

        messages.success(request, "Product added successfully.")
        return redirect('products')

    categories = Category.objects.filter(is_deleted=False)
    return render(request, 'admin_side/add_product.html', {'categories': categories})

# Delete product (soft delete)
def delete_product(request, product_id):
    product = Product.objects.get(serial_number=product_id)
    product.is_deleted = True  # Soft delete the product
    product.save()
    return redirect('products')

# Update product details
def update_product(request, product_id):
    product = Product.objects.get(serial_number=product_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        print(name)
        price = request.POST.get('price')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        category = Category.objects.get(id=category_id)
        stock = request.POST.get('stock')  # Update stock if needed

        # product.update(name) = name
        # product.price = price
        # product.description = description
        # product.category = category
        # product.stock = stock

        # Handle image update if necessary
        product_image = request.FILES.get('product_image')
        Product.objects.filter(serial_number=product.serial_number).update(
    name=name,
    price=price,
    description=description,
    category=category,
    stock=stock,
    images=product_image
)

        return redirect('products')

    categories = Category.objects.all()
    return render(request, 'admin_side/edit_product.html', {'product': product, 'categories': categories})

from django.db.models import Sum


from django.db.models import Sum
from django.shortcuts import render
from order.models import *
from product.models import *
from category.models import *

def admin_dashboard(request):
    # Best-selling products (Top 3)
    best_selling_products = OrderItem.objects.filter(
        order__status="Completed"
    ).values(
        'variant__product__name',  # Use product name for better clarity
    ).annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:3]

    # Best-selling categories (Top 3)
    best_selling_categories = OrderItem.objects.filter(
        order__status="Completed"
    ).values(
        'variant__product__category__name',  # Access category name through the product
    ).annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:3]

    # Best-selling brands (Top 3)
    best_selling_brands = OrderItem.objects.filter(
        order__status="Completed"
    ).values(
        'variant__product__brand__name',  # Access brand name through the product
    ).annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:3]

    # You can include other necessary data such as total sales, pending orders, etc.
    # Example: Calculate total sales
    total_sales = Order.objects.filter(status="Completed").aggregate(
        total_sales=Sum('total_price')
    )['total_sales'] or 0.0

    # Example: Calculate pending orders count
    pending_orders_count = Order.objects.filter(status="Pending").count()

    # Example: Total customers (distinct users who made purchases)
    total_customers = Order.objects.filter(status="Completed").values('user').distinct().count()

    # Example: Sales & Analytics (you can calculate percentage change as needed)
    sales_percentage_change = 12.5  # Placeholder, calculate based on your logic

    return render(request, 'admin_side/admin_dashboard.html', {
        'best_selling_products': best_selling_products,
        'best_selling_categories': best_selling_categories,
        'best_selling_brands': best_selling_brands,
        'total_sales': total_sales,
        'pending_orders_count': pending_orders_count,
        'total_customers': total_customers,
        'sales_percentage_change': sales_percentage_change,
    })


def admin_logout(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('admin_sign_in')



def contents(request):
    return render(request, 'admin_side/contents.html')

def settings(request):
    return render(request, 'admin_side/settings.html')

def coupon(request):
    return render(request, 'admin_side/coupon.html')

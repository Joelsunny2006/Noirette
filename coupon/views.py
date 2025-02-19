from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Coupon
from .forms import CouponForm
from cart.models import *
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from order.models import *
from django.utils.timezone import now
from admin_panel.decorator import admin_required 

# Admin-side Views
@admin_required 
def coupon_list(request):
    # Get query parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    discount_type_filter = request.GET.get('discount_type', '')
    sort_by = request.GET.get('sort', '-valid_from')  # Default sort by valid_from desc
    
    # Base queryset
    coupons = Coupon.objects.all()
    
    # Apply search
    if search_query:
        coupons = coupons.filter(
            Q(code__icontains=search_query) |
            Q(discount_value__icontains=search_query)
        )
    
    # Apply filters
    if status_filter:
        coupons = coupons.filter(status=status_filter)
    
    if discount_type_filter:
        coupons = coupons.filter(discount_type=discount_type_filter)
    
    # Update coupon statuses
    now = timezone.now()
    for coupon in coupons:
        if now < coupon.valid_from:
            new_status = 'upcoming'
        elif now > coupon.valid_to:
            new_status = 'expired'
        else:
            new_status = 'active'
        
        if coupon.usage_limit and coupon.current_usage >= coupon.usage_limit:
            new_status = 'expired'
            
        if new_status != coupon.status:
            coupon.status = new_status
            coupon.save(update_fields=['status'])
    
    # Apply sorting
    if sort_by.startswith('-'):
        coupons = coupons.order_by(sort_by, '-valid_from')  # Secondary sort by valid_from
    else:
        coupons = coupons.order_by(sort_by, 'valid_from')
    
    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(coupons, 10)  # 10 coupons per page
    page_obj = paginator.get_page(page_number)
    
    # Prepare context data
    context = {
        'coupons': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'discount_type_filter': discount_type_filter,
        'sort_by': sort_by,
        'total_coupons': coupons.count(),
        'active_coupons': coupons.filter(status='active').count(),
        'expired_coupons': coupons.filter(status='expired').count(),
        'upcoming_coupons': coupons.filter(status='upcoming').count(),
    }
    
    return render(request, 'admin_side/coupon.html', context)

@require_http_methods(["POST"])
@admin_required
def create_coupon(request):
    try:
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save()
            return JsonResponse({
                'status': 'success',
                'message': 'Coupon created successfully!',
                'coupon_id': coupon.id
            })
        else:
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = str(error_list[0])
            return JsonResponse({
                'status': 'error',
                'errors': errors
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred. Please try again.'
        }, status=500)

@admin_required
def edit_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    else:
        form = CouponForm(instance=coupon)

    return render(request, 'admin_side/coupon.html', {'form': form})

@admin_required
def delete_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.delete()
    messages.success(request, 'Coupon deleted successfully.')
    return redirect('coupon_list')

@login_required
def apply_coupon(request):
    try:
        cart = Cart.objects.get(user=request.user)
        coupon_code = request.POST.get('coupon_code')
        print(coupon_code)
        coupon = Coupon.objects.filter(code=coupon_code).first()

        print(coupon,"coupon")
        
        if not coupon:
            return JsonResponse({
                'status': 'error', 
                'message': 'Invalid coupon code.'
            })
        
        if not coupon.is_valid():
            return JsonResponse({
                'status': 'error', 
                'message': 'This coupon is no longer valid.'
            })
        
        # Calculate subtotal using the correct price logic
        subtotal = 0
        for item in cart.items.all():
            item_price = item.variant.get_discounted_price()
            subtotal += Decimal(item_price) * item.quantity

        delivery = Decimal('50.00')  # Delivery cost
        
        # Calculate discount based on coupon type
        if coupon.discount_type == 'percentage':
            discount = subtotal * (Decimal(coupon.discount_value) / 100)
        elif coupon.discount_type == 'fixed':
            discount = min(Decimal(coupon.discount_value), subtotal)
        else:
            return JsonResponse({
                'status': 'error', 
                'message': 'Invalid coupon type.'
            })
        
        # # Apply the coupon to the cart
        # cart.applied_coupon = coupon
        # cart.save()
        
        # Store coupon ID in session
        request.session['applied_coupon_id'] = coupon.id

        # Calculate total
        total = subtotal - discount + delivery 
        
        return JsonResponse({
            'status': 'success',
            'message': 'Coupon applied successfully.',
            'subtotal': float(subtotal),
            'delivery': float(delivery),
            'discount': float(discount),
            'total': float(total),
            'coupon_code': coupon.code,
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        })


@login_required
def remove_coupon(request):
    try:
        cart = Cart.objects.get(user=request.user)
        
        # Get the current subtotal using the correct price logic
        subtotal = 0
        for item in cart.items.all():
            item_price = item.variant.get_discounted_price()
            subtotal += Decimal(item_price) * item.quantity
        
        delivery = Decimal('50.00')  # Delivery cost
        
        # Remove the applied coupon
        cart.applied_coupon = None
        cart.save()

        # Remove coupon ID from session
        if 'applied_coupon_id' in request.session:
            del request.session['applied_coupon_id']
        
        # Recalculate total without discount
        total = subtotal + delivery
        
        return JsonResponse({
            'status': 'success',
            'message': 'Coupon removed successfully.',
            'subtotal': float(subtotal),
            'delivery': float(delivery),
            'discount': 0,
            'total': float(total),
            'coupon_code': '',
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        })


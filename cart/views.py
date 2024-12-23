from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem, Product, Variant
from django.shortcuts import render, redirect
from .forms import CheckoutForm
from django.contrib import messages
from decimal import Decimal
import logging
from .models import *
from order.models import *
from order.forms import AddressForm
from django.utils.timezone import now
from django.db.models import F, Sum

logger = logging.getLogger(__name__)


def add_to_cart(request):
    if request.method == "POST":
        try:
            variant_id = request.POST.get('variant_id')
            quantity = int(request.POST.get('quantity', 1))

            if not variant_id:
                messages.error(request, "No product selected.")
                return JsonResponse({'success': False, 'message': "No product selected."}, status=400)

            variant = get_object_or_404(Variant, id=variant_id)

            if request.user.is_authenticated:
                cart, _ = Cart.objects.get_or_create(user=request.user)
            else:
                session_id = request.session.get('session_id')
                if not session_id:
                    request.session.create()
                    session_id = request.session.session_key
                cart, _ = Cart.objects.get_or_create(session_id=session_id)

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                variant=variant,
                defaults={"quantity": quantity}
            )

            if not created:
                cart_item.quantity = 1  # Reset to 1 if quantity exceeds
                cart_item.save()

            return JsonResponse({
                'success': True,
                'message': "Item added to cart successfully!",
                'cart_total_items': cart.total_items,
            })

        except Exception as e:
            print("Error adding to cart:", e)
            return JsonResponse({'success': False, 'message': "An error occurred. Please try again."}, status=500)

    return JsonResponse({'success': False, 'message': "Invalid request method."}, status=405)


@login_required
def view_cart(request):
    # Ensure the cart exists for the authenticated user
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Get all items in the cart
    cart_items = CartItem.objects.filter(cart=cart)

    items = []
    total_price = 0

    for item in cart_items:
        # Access the Product through the Variant
        product = item.variant.product

        # Get the first image for the product (or default image)
        product_image = (
            product.images.first().image_url.url
            if product.images.exists()
            else '/static/images/default.jpg'
        )
        
        # Get the discounted price using the method `get_discounted_price`
        discounted_price = item.variant.get_discounted_price()
        if discounted_price is None:
            discounted_price = item.variant.variant_price
        display_price = discounted_price

        # Calculate total for each item
        item_total = display_price * item.quantity
        total_price += item_total

        items.append({
            'id': item.id,
            'product_name': product.name,
            'product_serial_number': product.serial_number,
            'product_slug': product.slug,
            'product_description': product.description,
            'product_thumbnail': product_image,
            'variant': item.variant.variant_name if item.variant else None,
            'variant_price': item.variant.variant_price,
            'discounted_price': discounted_price,
            'quantity': item.quantity,
            'total_price': item_total,
        })

    # Context for rendering the template
    context = {
        'items': items,
        'total_price': total_price,  # The total price of all items
    }

    return render(request, 'user_side/cart.html', context)



@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            return JsonResponse({'message': 'Cart item updated'})
        else:
            cart_item.delete()
            return JsonResponse({'message': 'Cart item removed'})
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
def remove_from_cart(request, item_id):
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            # Retrieve the cart item for the logged-in user
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            cart_item.delete()
            return JsonResponse({
                "success": True,
                "message": "Item removed from cart successfully!"
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"Error removing item from cart: {str(e)}"
            })
    return JsonResponse({
        "success": False,
        "message": "Invalid request. Ensure it's a POST AJAX request."
    })


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import json

@login_required
def update_cart_quantity(request, item_id):
    if request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Parse incoming request data
            data = json.loads(request.body)
            new_quantity = int(data.get('quantity', 0))

            # Validate quantity
            if new_quantity <= 0:
                return JsonResponse({"success": False, "message": "Quantity must be at least 1."})

            # Fetch the cart item and ensure it belongs to the user's cart
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            cart_item.quantity = new_quantity
            cart_item.save()

            # Calculate item-specific pricing
            item_price = cart_item.variant.get_discounted_price() or cart_item.variant.variant_price
            item_total_price = item_price * new_quantity

            # Update cart totals
            cart = cart_item.cart
            cart_total = cart.total_price()
            cart_total_after_discount = cart.total_price_after_discount()

            # Return updated values
            return JsonResponse({
                "success": True,
                "message": "Cart updated successfully.",
                "item_price": f"{item_price:.2f}",
                "item_total_price": f"{item_total_price:.2f}",
                "cart_total": f"{cart_total:.2f}",
                "cart_total_after_discount": f"{cart_total_after_discount:.2f}",
            })
        except CartItem.DoesNotExist:
            return JsonResponse({"success": False, "message": "Cart item not found."})
        except ValueError:
            return JsonResponse({"success": False, "message": "Invalid quantity provided."})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"An error occurred: {str(e)}"})

    # Invalid request method or headers
    return JsonResponse({"success": False, "message": "Invalid request."})


@login_required
def clear_cart(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart.items.all().delete()
    return JsonResponse({'message': 'Cart cleared'})

@login_required
def checkout_view(request, product_id=None):
    try:
        # Fetch user's cart and cart items
        cart = Cart.objects.get(user=request.user)

        # If a product_id is passed, add it to the cart
        if product_id:
            product = Product.objects.get(id=product_id)
            variant = product.variants.first()  # Assuming each product has at least one variant
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                variant=variant,
                defaults={'quantity': 1}
            )
            if not created:
                cart_item.quantity += 1
                cart_item.save()

        cart_items = CartItem.objects.filter(cart=cart)
        for item in cart_items:
            product = item.variant.product
            if product.offer_percentage:
                item.discounted_price = item.variant.variant_price * (1 - (product.offer_percentage / 100))
            else:
                item.discounted_price = item.variant.variant_price

        if not cart_items.exists():
            messages.error(request, 'Your cart is empty.')
            return redirect('view_cart')

        # Calculate cart subtotal
        subtotal = 0
        for item in cart_items:
            product = item.variant.product  # Access the product through the variant
            # Calculate offer price based on offer_percentage if applicable
            if product.offer_percentage:
                item_price = item.variant.variant_price * (1 - (product.offer_percentage / 100))
            else:
                item_price = item.variant.variant_price

            subtotal += Decimal(item_price) * item.quantity

        delivery = Decimal('50.00')  # Example delivery cost

        # Get the applied coupon, if any
        applied_coupon = cart.applied_coupon

        # Calculate the discount based on the applied coupon
        
        if applied_coupon:
            if applied_coupon.discount_type == 'percentage':
                discount = subtotal * (applied_coupon.discount_value / 100)
            elif applied_coupon.discount_type == 'fixed':
                discount = applied_coupon.discount_value

        # Calculate the total after discount
        total = subtotal + delivery

        # Fetch active coupons
        available_coupons = Coupon.objects.filter(
            status='active', 
            valid_from__lte=now(),
            valid_to__gte=now(),
        ).exclude(
            usage_limit__isnull=False,
            current_usage__gte=models.F('usage_limit')  # Exclude if usage_limit exceeded
        )
        
        # Cart count logic
        cart_count = cart_items.aggregate(total=models.Sum('quantity'))['total'] or 0

        # Fetch user's saved addresses
        addresses = Address.objects.filter(user=request.user)

        context = {
    'cart_items': cart_items,
    'available_coupons': available_coupons,
    'subtotal': subtotal,
    'delivery': delivery,
    'total': total,
    'cart_count': cart_count,
    'addresses': addresses,
}
        return render(request, 'user_side/checkout.html', context)

    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty.')
        return redirect('view_cart')
    except Product.DoesNotExist:
        messages.error(request, 'Product not found.')
        return redirect('view_cart')

@login_required
def add_address_view(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            # Save the new address
            new_address = form.save(commit=False)
            new_address.user = request.user
            new_address.save()

            # Redirect back to checkout with the newly added address
            messages.success(request, "Address added successfully. Redirecting to checkout...")
            return redirect('checkout')  # Redirect to the checkout page
    else:
        form = AddressForm()

    context = {
        'form': form,
    }
    return render(request, 'user_side/add_address.html', context)

from django.db.models import Sum

def wishlist(request):
    wishlist_items = []
    cart_count = 0

    if request.user.is_authenticated:
        try:
            # Retrieve the user's wishlist and related items
            wishlist = Wishlist.objects.filter(user=request.user).first()
            if wishlist:
                wishlist_items = wishlist.items.select_related('variant__product').all()
            
            # Retrieve the cart count
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart_count = cart.items.aggregate(total=Sum('quantity'))['total'] or 0
        except (Wishlist.DoesNotExist, Cart.DoesNotExist):
            pass

    return render(request, 'user_side/wishlist.html', {
        "cart_count": cart_count,
        "wishlist_items": wishlist_items
    })

# Add to Wishlist
def add_to_wishlist(request, variant_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=403)

    variant = get_object_or_404(Variant, id=variant_id)

    # Get or create the wishlist
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)

    # Check if the variant already exists in the wishlist
    if WishlistItem.objects.filter(wishlist=wishlist, variant=variant).exists():
        return JsonResponse({"message": "Variant already in wishlist"}, status=400)

    # Add the variant to the wishlist
    WishlistItem.objects.create(wishlist=wishlist, variant=variant)
    return JsonResponse({"message": "Variant added to wishlist"}, status=201)


# Remove from Wishlist
@csrf_exempt
def remove_from_wishlist(request, variant_id):
    if request.method == 'POST':
        try:
            # Retrieve the user's wishlist
            wishlist = Wishlist.objects.get(user=request.user)
            # Find the item to remove
            wishlist_item = get_object_or_404(WishlistItem, wishlist=wishlist, variant_id=variant_id)
            wishlist_item.delete()

            # Optionally, return the updated wishlist count
            updated_count = wishlist.items.count()

            return JsonResponse({
                'success': True,
                'message': 'Item successfully removed from wishlist.',
                'updated_count': updated_count
            })
        except Wishlist.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Wishlist does not exist.'})
        except WishlistItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item does not exist in wishlist.'})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})

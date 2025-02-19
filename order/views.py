from django.shortcuts import render, redirect
from .models import *
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from order.models import Address
from .forms import AddressForm
from django.contrib.auth.decorators import login_required
import logging
from .forms import CheckoutForm
from cart.models import *
from decimal import Decimal
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import razorpay
from wallet.models import *
from product.models import *
from django.http import HttpResponseNotAllowed
from django.http import HttpResponse 
from django.contrib.messages import get_messages
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_control
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required
            # Handle different payment methods
import logging
import razorpay
from django.conf import settings
from django.shortcuts import render
from django.urls import reverse
from admin_panel.decorator import admin_required 
from django.core.paginator import Paginator


import os
from io import BytesIO
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from weasyprint import HTML, CSS

@require_http_methods(["GET"])
@admin_required
def orders(request):
    orders_list = Order.objects.select_related("user").all().order_by("-created_at")

    # Pagination: Show 10 orders per page
    paginator = Paginator(orders_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "admin_side/orders.html",
        {"page_obj": page_obj},
    )

@csrf_protect
@require_http_methods(["POST"])
def update_order_status(request, order_id):

    try:
        # Fetch the order
        order = get_object_or_404(Order, id=order_id)

        # Get the new status from the POST request
        new_status = request.POST.get("status")

        # Validate status
        valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({"error": "Invalid status!"}, status=400)

        # Update the order
        order.status = new_status
        order.save()

        # Return success response
        return JsonResponse(
            {
                "message": f"Order #{order_id} status updated to {new_status} successfully!",
                "new_status": new_status,
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_protect
@require_http_methods(["POST"])
def delete_order(request, order_id):
    try:
        # Fetch and delete the order
        order = get_object_or_404(Order, id=order_id)
        order.delete()

        # Return success response
        return JsonResponse({"message": f"Order #{order_id} deleted successfully!"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def address_list(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, "user_side/user_profile.html", {"addresses": addresses})


def save_address(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user  
            address.save()
            messages.success(request, "Address saved successfully!")  # Success message
        else:
            messages.error(request, "Failed to save address. Please try again.")  # Error message
    return redirect("user_profile")  # Redirect back to profile

@login_required
def delete_address(request, address_id):
    if request.method == "POST":
        address = get_object_or_404(Address, id=address_id, user=request.user)

        # Prevent deleting the only address
        if Address.objects.filter(user=request.user).count() <= 1:
            messages.error(request, "You cannot delete your only address.")
        else:
            address.delete()
            messages.success(request, "Address deleted successfully.")

    return redirect("user_profile")


@login_required
def edit_address(request, address_id):
    """
    Fetch the address data as JSON for editing.
    """
    address = get_object_or_404(Address, id=address_id, user=request.user)

    # Return JSON response for pre-filling modal
    return JsonResponse(
        {
            "id": address.id,
            "first_name": address.first_name,
            "last_name": address.last_name,
            "street_address": address.street_address,
            "apartment": address.apartment,
            "city": address.city,
            "state": address.state,
            "postcode": address.postcode,
            "phone": address.phone,
            "email": address.email
        }
    )

from django.contrib import messages

# views.py
@login_required
def place_order(request):
    if request.method == "POST":
        try:
            # Get data from the form
            payment_method = request.POST.get("payment_method")
            selected_address_id = request.POST.get("saved_address")

            # Normalize payment method string
            payment_method = payment_method.lower() if payment_method else None

            # Check if a shipping address is selected
            if not selected_address_id:
                messages.error(request, "Please select a valid shipping address.")
                return redirect("checkout")

            # Retrieve the selected address
            try:
                address = Address.objects.get(id=selected_address_id, user=request.user)
            except Address.DoesNotExist:
                messages.error(request, "Selected address does not exist.")
                return redirect("checkout")

            # Get cart and validate items
            cart = Cart.objects.get(user=request.user)
            cart_items = CartItem.objects.filter(cart=cart).select_related(
                "variant", 
                "variant__product", 
                "variant__product__category", 
                "variant__product__brand"
            )

            if not cart_items.exists():
                messages.error(request, "Your cart is empty.")
                return redirect("cart")

            # Check for invalid items
            invalid_items = []
            for item in cart_items:
                if (
                    item.variant.variant_stock <= 0 or 
                    item.variant.product.is_deleted or 
                    not item.variant.product.category.status or 
                    item.variant.product.category.is_deleted or 
                    item.variant.product.brand and item.variant.product.brand.status == "inactive"
                ):
                    invalid_items.append(item)

            if invalid_items:
                messages.error(request, "Some items in your cart are no longer available. Please remove them to proceed.")
                return redirect("cart")

            # Calculate totals including discounts
            subtotal = sum(
                Decimal(str(item.variant.get_discounted_price())) * item.quantity
                for item in cart_items
            )
            delivery = Decimal('50.00')
            discount = Decimal('0.00')

            # Check if a coupon ID exists in the session
            coupon_id = request.session.get('applied_coupon_id')
            if coupon_id:
                try:
                    coupon = Coupon.objects.get(id=coupon_id)
                    if coupon.discount_type == 'percentage':
                        discount = subtotal * (coupon.discount_value / 100)
                    else:
                        discount = coupon.discount_value
                except Coupon.DoesNotExist:
                    coupon = None
                    discount = Decimal('0.00')

            # Ensure total price is not negative
            total_price = max(subtotal + delivery - discount, Decimal('0.00'))
            if payment_method == "wallet":
                wallet = Wallet.objects.get(user=request.user)
                if wallet.balance < total_price:
                    messages.error(request, "Insufficient wallet balance.")
                    return redirect("checkout")
                
            # Create order address
            order_address = OrderAddress.objects.create(
                user=request.user,
                name=f"{address.first_name} {address.last_name}",
                phone_number=address.phone,
                house_name=address.apartment,
                street_name=address.street_address,
                district=address.city,
                state=address.state,
                country="India",
                pin_number=address.postcode,
            )

            # Create order with coupon and discount applied
            order = Order.objects.create(
                user=request.user,
                status="Pending",
                total_price=total_price,
                order_address=order_address,
                payment_method=payment_method,
                coupon=coupon if coupon_id else None,  # Store applied coupon
                coupon_discount=discount  # Store discount amount
            )

            # Create order items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    quantity=item.quantity,
                    total_price=Decimal(item.variant.variant_price) * item.quantity,
                )

            # Clear applied coupon from session
            if 'applied_coupon_id' in request.session:
                del request.session['applied_coupon_id']


            if payment_method == "razorpay":
                try:
                    # Create Razorpay client
                    client = razorpay.Client(
                        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                    )

                    # Create Razorpay order
                    amount_in_paise = int(total_price * 100)  # Convert to paise
                    razorpay_order = client.order.create({
                        "amount": amount_in_paise,
                        "currency": "INR",
                        "receipt": f"order_rcptid_{order.id}",
                        "payment_capture": "1",
                    })

                    # Save order details
                    order.razorpay_order_id = razorpay_order["id"]
                    order.status = "Payment Pending"
                    cart_items.delete() 
                    order.save()

                    # Prepare context for the Razorpay payment page
                    context = {
                        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                        "amount": amount_in_paise,
                        "razorpay_order_id": razorpay_order["id"],
                        "order_id": order.id,
                        "callback_url": request.build_absolute_uri(reverse('order:verify_payment'))
                    }

                    return render(request, "user_side/razorpay_payment.html", context)

                except razorpay.errors.RazorpayError as e:
                    logger.error(f"Razorpay error: {e}")
                    messages.error(request, "Payment processing failed. Please try again.")
                    return redirect("checkout")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    messages.error(request, "An unexpected error occurred. Please contact support.")
                    return redirect("checkout")

            elif payment_method == "cod":
                if total_price > 1000:
                    messages.error(request, "COD not available for orders above ₹1000")
                    return redirect("checkout")

                order.status = "Processing"
                order.save()
                cart_items.delete()  # Clear cart after successful order
                messages.success(request, "Order placed successfully with Cash on Delivery.")
                return redirect("order:order_success")

            elif payment_method == "wallet":
                try:
                    wallet = Wallet.objects.get(user=request.user)
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        amount=total_price,
                        transaction_type="debit",
                        description=f"Payment for order #{order.id}",
                    )

                    wallet.balance -= total_price
                    wallet.save()

                    order.status = "Processing"
                    order.save()

                    cart_items.delete()  # Clear cart after successful order

                    messages.success(request, "Order placed successfully using wallet!")
                    return redirect("order:order_success")
       
                except Wallet.DoesNotExist:
                    messages.error(request, "Wallet does not exist.")
                    return redirect("checkout")

            else:
                messages.error(request, "Invalid payment method.")
                return redirect("checkout")

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            messages.error(request, "An unexpected error occurred. Please try again.")
            return redirect("checkout")

    return redirect("checkout")





import logging

logger = logging.getLogger(__name__)  # Add this at the top
from django.http import HttpResponseRedirect

import json

@csrf_exempt
def verify_payment(request):
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Get JSON request data
            
            razorpay_order_id = data.get("razorpay_order_id")
            razorpay_payment_id = data.get("razorpay_payment_id")
            razorpay_signature = data.get("razorpay_signature")

            if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
                return JsonResponse({"error": "Missing required parameters"}, status=400)

            # Verify payment signature
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })

            # Update order status
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
            order.status = "Processing"
            order.save()

            # Clear cart
            CartItem.objects.filter(cart__user=order.user).delete()

            return JsonResponse({"success": True, "message": "Payment successful!"})

        except razorpay.errors.SignatureVerificationError as e:
            return JsonResponse({"success": False, "error": "Payment verification failed."}, status=400)

        except Order.DoesNotExist:
            return JsonResponse({"success": False, "error": "Order not found."}, status=400)

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)




@login_required
def razorpay_payment(request):
    if request.method == "POST":
        order_id = request.POST.get("order_id")
        try:
            # Debugging
            print("Order ID:", order_id)

            # Get the order and cart
            order = Order.objects.get(id=order_id, user=request.user)
            cart = Cart.objects.get(user=request.user)

            # Recalculate totals
            cart_items = CartItem.objects.filter(cart=cart)
            subtotal = sum(
                (item.variant.product.offer_price if item.variant.product.offer_price else item.variant.variant_price)
                * item.quantity
                for item in cart_items
            )
            delivery = Decimal('50.00')
            discount = Decimal('0.00')

            applied_coupon = cart.applied_coupon
            if applied_coupon:
                if applied_coupon.discount_type == 'percentage':
                    discount = subtotal * (applied_coupon.discount_value / 100)
                elif applied_coupon.discount_type == 'fixed':
                    discount = applied_coupon.discount_value

            total_amount = subtotal + delivery - discount
            total_amount_in_paise = int(total_amount * 100)

            # Create Razorpay order
            razorpay_client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            data = {
                "amount": total_amount_in_paise,
                "currency": "INR",
                "receipt": f"order_rcptid_{order.id}",
            }
            razorpay_order = razorpay_client.order.create(data=data)

            # Render payment page
            context = {
                "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                "amount": total_amount,
                "razorpay_order_id": razorpay_order["id"],
                "order_id": order.id,
            }
            return render(request, "user_side/razorpay_payment.html", context)

        except Order.DoesNotExist:
            messages.error(request, "Order not found for ID: " + str(order_id))
            return redirect("checkout")
        except Cart.DoesNotExist:
            messages.error(request, "Cart not found for user: " + str(request.user))
            return redirect("checkout")
        except razorpay.errors.RazorpayError as e:
            messages.error(request, f"Razorpay error: {str(e)}")
            return redirect("checkout")
        except Exception as e:
            messages.error(request, f"Unexpected error: {str(e)}")
            return redirect("checkout")

    return redirect("checkout") 

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def order_success(request):
    response = render(request, "user_side/order_success.html")
    return response

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def order_failure(request):
    response = render(request, "user_side/order_failure.html")
    return response


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status in ["Pending", "Processing", "Shipped"]:
        try:
            # Restore stock for each item in the order
            for item in order.items.all():
                item.variant.variant_stock += item.quantity
                item.variant.save()

            # Process wallet refund (if applicable)
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            wallet.balance += Decimal(str(order.total_price))  
            wallet.save()
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=order.total_price,
                transaction_type="credit",
                description=f"Refund for Cancelled Order #{order_id}",
            )

            # Update order status
            order.status = "Cancelled"
            order.save()

            messages.success(request, f"Order #{order_id} has been cancelled. Refund of ₹{order.total_price} has been added to your wallet.")
        except Exception as e:
            messages.error(request, f"Error processing cancellation: {str(e)}")
    else:
        messages.error(request, "This order cannot be cancelled.")

    return redirect("user_profile")

@login_required
def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Allow return request only if it's 'Completed' and hasn't been requested already
    if order.status == "Completed":
        if order.return_request_status == "None":
            if request.method == "POST":
                return_reason = request.POST.get("return_reason", "")
                order.return_request_status = "Pending"
                order.return_reason = return_reason
                order.save()
                messages.success(request, "Your return request has been submitted for approval.")
            else:
                messages.error(request, "Invalid request.")

        elif order.return_request_status == "Rejected":
            messages.error(request, "Your return request has been rejected. You cannot request a return again.")

        else:
            messages.error(request, "This order cannot be returned at this stage.")

    else:
        messages.error(request, "This order cannot be returned.")

    return redirect("user_profile")


@staff_member_required
def manage_returns(request):
    pending_returns = Order.objects.filter(return_request_status="Pending")
    return render(request, "admin_side/manage_returns.html", {"pending_returns": pending_returns})


@staff_member_required
def approve_return(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.return_request_status == "Pending":
        # Restore stock
        for item in order.items.all():
            item.variant.variant_stock += item.quantity
            item.variant.save()

        # Refund to wallet
        wallet, _ = Wallet.objects.get_or_create(user=order.user)
        wallet.balance += Decimal(str(order.total_price))
        wallet.save()
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=order.total_price,
            transaction_type="credit",
            description=f"Refund for Order #{order_id} return",
        )

        # Update order status
        order.status = "Returned"
        order.return_request_status = "Approved"
        order.save()

        messages.success(request, f"Return request for Order #{order_id} approved.")
    return redirect("order:manage_returns")

@staff_member_required
def reject_return(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.return_request_status == "Pending":
        order.return_request_status = "Rejected"
        order.save()
        messages.error(request, f"Return request for Order #{order_id} rejected.")
    return redirect("order:manage_returns")



@login_required
def continue_payment(request, order_id):
    try:
        # Fetch the order with "Payment Failed" or "Payment Pending" status
        order = Order.objects.get(
            id=order_id, 
            user=request.user, 
            status__in=["Payment Failed", "Payment Pending"]
        )
        total_amount = order.total_price
        total_amount_in_paise = int(total_amount * 100)  # Convert to paise for Razorpay

        # Initialize Razorpay Client
        razorpay_client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        
        # Create a new Razorpay order
        razorpay_order = razorpay_client.order.create({
            "amount": total_amount_in_paise,
            "currency": "INR",
            "receipt": f"retry_payment_{order.id}",
        })

        # Update the Razorpay order ID for retry
        order.razorpay_order_id = razorpay_order["id"]
        order.status = "Payment Pending"  # Reset status
        order.save()

        # Pass data to the payment template
        context = {
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "amount": float(total_amount),  # Ensure it's a float
            "razorpay_order_id": razorpay_order["id"],
            "order_id": order.id,
        }
        
        # If it's an AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(context)
        
        # Regular request, render template
        return render(request, "user_side/razorpay_payment.html", context)

    except Order.DoesNotExist:
        messages.error(request, "No order found with payment status.")
        return redirect("user_profile")

    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {e}")
        return redirect("user_profile")
    
@login_required
def download_invoice(request, order_id):
    try:
        # Fetch order and related data
        order = get_object_or_404(Order, id=order_id)
        order_items = order.items.all()

        # Define invoice styles
        invoice_css = """
        @page { size: A4; margin: 20mm; }
        body { font-family: 'Noto Sans', sans-serif; font-size: 12px; color: #333; }
        h1 { text-align: center; font-size: 20px; margin-bottom: 10px; }
        h2 { font-size: 16px; margin-bottom: 5px; }
        p { margin: 5px 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #f4f4f4; font-weight: bold; }
        .total { text-align: right; font-weight: bold; }
        """

        # Generate invoice content as HTML
        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>Invoice #{order.id}</title>
        </head>
        <body>
            <h1>Noirette</h1>
            <h2>Order Invoice</h2>

            <p><b>Order Number:</b> {order.id}</p>
            <p><b>Order Date:</b> {order.created_at.strftime('%B %d, %Y')}</p>
            <p><b>Customer Name:</b> {order.order_address.name}</p>
            <p><b>Email:</b> {order.user.email}</p>
            <p><b>Phone:</b> {order.order_address.phone_number}</p>
            <p><b>Address:</b> {order.order_address.house_name}, {order.order_address.street_name}, 
               {order.order_address.district}, {order.order_address.state}, {order.order_address.pin_number}, 
               {order.order_address.country}</p>

            <table>
                <tr>
                    <th>Variant</th>
                    <th>Quantity</th>
                    <th>Unit Price</th>
                    <th>Total Price</th>
                </tr>
        """

        subtotal = Decimal('0.00')
        delivery_charge = Decimal('50.00')

        for item in order_items:
            variant = item.variant  # Access the Variant instance
            item_total_price = Decimal(item.total_price)
            subtotal += item_total_price

            html_content += f"""
                <tr>
                    <td>{variant.variant_name}</td>
                    <td>{item.quantity}</td>
                    <td>₹{variant.variant_price:.2f}</td>
                    <td>₹{item_total_price:.2f}</td>
                </tr>
            """

        # Apply Coupon Discount
        coupon_discount = order.coupon_discount if order.coupon else Decimal('0.00')
        total_amount = subtotal + delivery_charge - coupon_discount

        if order.coupon:
            html_content += f"""
                <p><b>Coupon Code:</b> {order.coupon.code}</p>
                <p><b>Discount Applied:</b> ₹{coupon_discount:.2f}</p>
            """

        html_content += f"""
            </table>
            <p class="total">Subtotal: ₹{subtotal:.2f}</p>
            <p class="total">Delivery: ₹{delivery_charge:.2f}</p>
            <p class="total"><b>Discount:</b> -₹{coupon_discount:.2f}</p>
            <p class="total"><b>Total: ₹{total_amount:.2f}</b></p>

            <p>Thank you for shopping with Noirette!</p>
        </body>
        </html>
        """

        # Convert HTML to PDF
        pdf_file = BytesIO()
        HTML(string=html_content).write_pdf(pdf_file, stylesheets=[CSS(string=invoice_css)])

        # Return the PDF as a response
        pdf_file.seek(0)
        response = HttpResponse(pdf_file.read(), content_type="application/pdf")
        response['Content-Disposition'] = f'attachment; filename="invoice_{order_id}.pdf"'
        return response

    except Exception as e:
        return HttpResponse(f'Error generating PDF: {str(e)}', status=500)


def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Fetch images for each variant
    order_items = []
    for item in order.items.all():
        first_image = ProductImage.objects.filter(product=item.variant.product).first()
        order_items.append({
            'item': item,
            'image_url': first_image.image_url.url if first_image else None
        })

    return render(request, 'user_side/order_detail.html', {'order': order, 'order_items': order_items})


def order_detail_admin(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Fetch images for each variant
    order_items = []
    for item in order.items.all():
        first_image = ProductImage.objects.filter(product=item.variant.product).first()
        order_items.append({
            'item': item,
            'image_url': first_image.image_url.url if first_image else None
        })

    context = {
        'order': order,
        'order_items': order_items,
        'admin_view': True  # Add this to differentiate admin view
    }
    
    return render(request, 'admin_side/order_detail.html', context)
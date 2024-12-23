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
from django.http import HttpResponseNotAllowed
from django.http import HttpResponse 
from django.contrib.messages import get_messages
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_control
from django.urls import reverse
            # Handle different payment methods
import logging
import razorpay
from django.conf import settings
from django.shortcuts import render
from django.urls import reverse



@require_http_methods(["GET"])
def orders(request):
    orders = Order.objects.select_related("user").all().order_by("-created_at")
    return render(
        request,
        "admin_side/orders.html",
        {
            "orders": orders,
        },
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
        if request.POST.get("address_id"):
            # Editing an address
            address = get_object_or_404(Address, id=request.POST.get("address_id"))
            form = AddressForm(request.POST, instance=address)
        else:
            # Creating a new address
            form = AddressForm(request.POST)

        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user  
            address.save()
            return redirect("order:address_list")
        else:
            print(
                "Form errors:", form.errors
            )  # Debugging - see why the form is invalid
            return JsonResponse({"error": "Invalid data"}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


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

            # Get cart and calculate totals
            cart = Cart.objects.get(user=request.user)
            cart_items = CartItem.objects.filter(cart=cart).select_related("variant")

            if not cart_items.exists():
                messages.error(request, "Your cart is empty.")
                return redirect("cart")

            # Calculate totals including discounts
            subtotal = sum(
                Decimal(item.variant.variant_price) * item.quantity
                for item in cart_items
            )
            delivery = Decimal('50.00')
            discount = Decimal('0.00')

            # Check if a coupon ID exists in the session
            coupon_id = request.session.get('applied_coupon_id')
            if coupon_id:
                coupon = Coupon.objects.get(id=coupon_id)
                if coupon.discount_type == 'percentage':
                    discount = subtotal * (coupon.discount_value / 100)
                else:
                    discount = coupon.discount_value

            total_price = subtotal + delivery - discount

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

            # Create order
            order = Order.objects.create(
                user=request.user,
                status="Pending",
                total_price=total_price,
                order_address=order_address,
                payment_method=payment_method
            )

            # Create order items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    quantity=item.quantity,
                    total_price=Decimal(item.variant.variant_price) * item.quantity,
                )

            # Clear the applied coupon from the session
            if 'applied_coupon_id' in request.session:
                del request.session['applied_coupon_id']


            # Configure logging
            logging.basicConfig(level=logging.DEBUG)
            logger = logging.getLogger(__name__)

            if payment_method == "razorpay":

                logger.debug("Payment method is Razorpay.")
                
                try:
                    # Create Razorpay client
                    client = razorpay.Client(
                        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                    )
                    logger.debug("Razorpay client created successfully.")

                    # Ensure total_price is a valid number
                    logger.debug(f"Total price: {total_price}")
                    
                    # Create Razorpay order
                    amount_in_paise = int(total_price * 100)  # Convert to paise
                    logger.debug(f"Amount in paise: {amount_in_paise}")

                    razorpay_order = client.order.create({
                        "amount": amount_in_paise,
                        "currency": "INR",
                        "receipt": f"order_rcptid_{order.id}",
                        "payment_capture": "1",
                    })
                    logger.debug(f"Razorpay order created: {razorpay_order}")

                    # Save order details
                    order.razorpay_order_id = razorpay_order["id"]
                    order.status = "Payment Pending"
                    order.save()
                    logger.debug(f"Order updated with Razorpay order ID: {order.razorpay_order_id}")

                    # Prepare context for the Razorpay payment page
                    context = {
                        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                        "amount": amount_in_paise,
                        "razorpay_order_id": razorpay_order["id"],
                        "order_id": order.id,
                        "callback_url": request.build_absolute_uri(reverse('order:verify_payment'))
                    }
                    logger.debug(f"Context for payment page: {context}")

                    return render(request, "user_side/razorpay_payment.html", context)

                except razorpay.errors.RazorpayError as e:
                    logger.error(f"Razorpay error: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    raise


            elif payment_method == "cod":
                if total_price > 1000:
                    messages.error(request, "COD not available for orders above ₹1000")
                    return redirect("checkout")

                order.status = "Processing"
                order.save()
                cart_items.delete()  # Clear cart after successful order
                messages.success(request, "Order placed successfully with Cash on Delivery.")
                return redirect("order:order_success")  # Make sure this URL name matches your urls.py

            elif payment_method == "wallet":
                try:
                    wallet = Wallet.objects.get(user=request.user)
                    if wallet.balance >= total_price:
                        # Create wallet transaction
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
                        return redirect("order:order_success")  # Make sure this URL name matches your urls.py
                    else:
                        messages.error(request, "Insufficient wallet balance.")
                        return redirect("checkout")
                except Wallet.DoesNotExist:
                    messages.error(request, "Wallet does not exist.")
                    return redirect("checkout")

            else:
                messages.error(request, "Invalid payment method.")
                return redirect("checkout")

        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {str(e)}")
            return redirect("checkout")

    return redirect("checkout")

        


def verify_payment(request):
    if request.method == "POST":
        # Extract Razorpay payment details from the POST data
        razorpay_order_id = request.POST.get("razorpay_order_id")
        razorpay_payment_id = request.POST.get("razorpay_payment_id")
        razorpay_signature = request.POST.get("razorpay_signature")

        # Print the extracted Razorpay details for debugging
        print(f"Razorpay details received: order_id={razorpay_order_id}, payment_id={razorpay_payment_id}, signature={razorpay_signature}")

        try:
            # Verify Razorpay signature
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            params = {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
            client.utility.verify_payment_signature(params)

            # Print confirmation of successful verification
            print("Razorpay payment signature verified successfully.")

            # Retrieve the order object based on the Razorpay order ID
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
            print(f"Order found for Razorpay order ID: {razorpay_order_id}. Updating status.")

            # Update the order status to 'Processing' if payment is successful
            order.status = "Processing"
            order.save()
            print(f"Order status updated to 'Processing' for order ID: {order.id}")

            # Clear cart items for the user
            CartItem.objects.filter(cart__user=order.user).delete()
            print(f"Cart items cleared for user: {order.user.id}")

            # Redirect to order success page
            messages.success(request, "Payment successful!")
            return redirect("order:order_success")

        except razorpay.errors.SignatureVerificationError as e:
            print(f"Razorpay signature verification failed: {str(e)}")
            messages.error(request, "Payment verification failed. Please try again.")
            # Clear cart items in case of failure to avoid stuck items
            CartItem.objects.filter(cart__user=request.user).delete()
            return redirect("order:order_failure")

        except Order.DoesNotExist:
            print(f"Order with Razorpay order ID {razorpay_order_id} not found.")
            return HttpResponseBadRequest("Invalid order ID.")

        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            messages.error(request, "An unexpected error occurred. Please contact support.")
            # Clear cart items in case of failure to avoid stuck items
            CartItem.objects.filter(cart__user=request.user).delete()
            return redirect("order:order_failure")
    else:
        print("Received non-POST request for payment verification.")
        return HttpResponseBadRequest("Invalid request method.")


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

            # Debugging Razorpay order
            print("Razorpay Order Created:", razorpay_order)

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
    return render(request, "user_side/order_success.html")

@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def order_failure(request):
    return render(request, "user_side/order_failure.html")


@login_required
def cancel_order(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Only allow cancellation for pending or processing orders
    if order.status in ["Pending", "Processing","Shipped"]:
        # Process wallet refund
        try:
            # Create or get user's wallet
            wallet, created = Wallet.objects.get_or_create(user=request.user)

            # Create wallet transaction
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=order.total_price,
                transaction_type="credit",
                description=f"Refund for Cancelled Order #{order_id}",
            )

            # Update order status
            order.status = "Cancelled"
            order.save()

            messages.success(
                request,
                f"Order #{order_id} has been cancelled. Refund of ₹{order.total_price} has been added to your wallet.",
            )

        except Exception as e:
            messages.error(request, f"Error processing cancellation: {str(e)}")
    else:
        messages.error(request, "This order cannot be cancelled.")

    return redirect("user_profile")  # Adjust this to your profile URL name


@login_required
def return_order(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Only allow returns for completed orders
    if order.status == "Completed":
        try:
            # Create or get user's wallet
            wallet, created = Wallet.objects.get_or_create(user=request.user)

            # Create wallet transaction
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=order.total_price,
                transaction_type="credit",
                description=f"Refund for Returned Order #{order_id}",
            )

            # Update order status
            order.status = "Returned"
            order.save()

            messages.success(
                request,
                f"Order #{order_id} has been returned. Refund of ₹{order.total_price} has been added to your wallet.",
            )

        except Exception as e:
            messages.error(request, f"Error processing return: {str(e)}")
    else:
        messages.error(request, "This order cannot be returned.")

    return redirect("user_profile")  # Adjust this to your profile URL name



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
    

from io import BytesIO
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

@login_required
def download_invoice(request, order_id):
    try:
        # Fetch order and related data
        order = get_object_or_404(Order, id=order_id)
        order_items = order.items.all()
        buffer = BytesIO()

        try:
            # Create PDF
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40
            )
            elements = []

            # Styles
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            subtitle_style = ParagraphStyle(name="Subtitle", fontSize=14, leading=18, spaceAfter=12)
            normal_style = styles['Normal']

            # Invoice Header
            elements.append(Paragraph("Noirette", title_style))
            elements.append(Paragraph("Order Invoice", subtitle_style))
            elements.append(Spacer(1, 0.5 * inch))

            # Order Details
            elements.append(Paragraph(f"<b>Order Number:</b> {order.id}", normal_style))
            elements.append(Paragraph(f"<b>Order Date:</b> {order.created_at.strftime('%B %d, %Y')}", normal_style))
            elements.append(Paragraph(f"<b>Customer Name:</b> {order.order_address.name}", normal_style))
            elements.append(Paragraph(f"<b>Email:</b> {order.user.email}", normal_style))
            elements.append(Paragraph(f"<b>Phone:</b> {order.order_address.phone_number}", normal_style))
            elements.append(Paragraph(
                f"<b>Address:</b> {order.order_address.house_name}, {order.order_address.street_name}, "
                f"{order.order_address.district}, {order.order_address.state}, {order.order_address.pin_number}, "
                f"{order.order_address.country}",
                normal_style
            ))
            elements.append(Spacer(1, 0.5 * inch))

            # Order Items Table
            data = [['Variant', 'Quantity', 'Unit Price', 'Total Price']]
            subtotal = Decimal('0.00')
            Delivery = Decimal('50.00')

            for item in order_items:
                variant = item.variant  # Access the Variant instance
                item_total_price = Decimal(item.total_price)
                subtotal += item_total_price

                data.append([
                    Paragraph(variant.variant_name, normal_style),
                    str(item.quantity),
                    f"${variant.variant_price:.2f}",
                    f"${item_total_price:.2f}"
                ])

            table = Table(data, colWidths=[None, 1.25 * inch, 1.25 * inch, 1.5 * inch])
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 11),
                ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            ])
            table.setStyle(style)
            elements.append(table)

            # Order Total
            elements.append(Spacer(1, 0.5 * inch))
            total_data = [
                ['Subtotal:', f"${subtotal:.2f}"],
                ['Delivery:', f"${Delivery:.2f}"],
                ['Total:', f"${(subtotal + Delivery):.2f}"]
            ]

            total_table = Table(total_data, colWidths=[4 * inch, 1.5 * inch], hAlign='RIGHT')
            total_table_style = TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black)
            ])
            total_table.setStyle(total_table_style)
            elements.append(total_table)

            # Footer
            elements.append(Spacer(1, 1 * inch))
            elements.append(Paragraph("Thank you for shopping with Noirette!", normal_style))

            # Build PDF
            doc.build(elements)
        except Exception as e:
            return HttpResponse(f'Error generating PDF content: {str(e)}', status=500)

        # Return PDF Response
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f'invoice_{order_id}.pdf')

    except Exception as e:
        return HttpResponse(f'Error generating PDF: {str(e)}', status=500)

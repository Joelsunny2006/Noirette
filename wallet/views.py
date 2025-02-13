from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import *
from cart.models import *
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from decimal import Decimal

@login_required
def wallet_view(request):
    """
    Display wallet summary including total credited, total debited, net balance, transaction history,
    cart count, wishlist count, and wallet balance.
    """
    try:
        wallet, created = Wallet.objects.get_or_create(user=request.user)


        print(wallet.balance)

        # Calculate total credited amount
        total_credited = (
            wallet.transactions.filter(transaction_type='credit')
            .aggregate(total=Sum('amount'))['total'] or 0
        )

        # Calculate total debited amount
        total_debited = (
            wallet.transactions.filter(transaction_type='debit')
            .aggregate(total=Sum('amount'))['total'] or 0
        )

        # Fetch transaction history
        transactions = wallet.transactions.all().order_by('-timestamp')  # Latest first

        # Calculate net balance
        net_balance = total_credited - total_debited

        # Initialize counts
        cart_count = 0
        wishlist_count = 0
        wallet_balance = 0

        # Get Cart Count
        try:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart_count = cart.items.aggregate(total=Sum('quantity'))['total'] or 0
        except Cart.DoesNotExist:
            cart_count = 0

        # Get Wishlist Count
        try:
            wishlist = Wishlist.objects.filter(user=request.user).first()
            if wishlist:
                wishlist_count = wishlist.items.count()
        except Wishlist.DoesNotExist:
            wishlist_count = 0

        # Get Wallet Balance
        try:
            if wallet:
                wallet_balance = wallet.balance
        except Wallet.DoesNotExist:
            wallet_balance = 0

        context = {
            'total_credited': total_credited,
            'total_debited': total_debited,
            'net_balance': net_balance,
            'transactions': transactions,
            'cart_count': cart_count,
            'wishlist_count': wishlist_count,
            'wallet_balance': wallet_balance,
        }

        return render(request, 'user_side/wallet.html', context)

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('wallet_view')  # Adjust the redirect as needed


def process_wallet_refund(order):
    """
    Process refund to wallet for cancelled or returned orders
    """
    try:
        # Create or get user's wallet
        wallet, created = Wallet.objects.get_or_create(user=order.user)
        
        # Create wallet transaction
        transaction_type = 'credit'
        description = f"Refund for Order #{order.id}"
        
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=order.total_price,
            transaction_type=transaction_type,
            description=description
        )
        
        return True
    except Exception as e:
        # Log the error
        print(f"Wallet refund error: {str(e)}")
        return False



# Razorpay Client Setup
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

@login_required
def create_wallet_razorpay_order(request):
    """
    Create a Razorpay order for wallet funding
    """
    try:
        # Get the amount to add to wallet from request
        amount = request.POST.get('amount', 0)
        amount = float(amount) * 100  # Convert to paisa

        # Create Razorpay Order
        order_data = {
            'amount': int(amount),  # amount in paisa
            'currency': 'INR',
            'receipt': f'wallet_funding_{request.user.id}_{timezone.now().timestamp()}',
            'payment_capture': 1
        }
        
        order = razorpay_client.order.create(order_data)
        
        return JsonResponse({
            'key': settings.RAZORPAY_KEY_ID,
            'amount': order_data['amount'],
            'order_id': order['id'],
            'name': 'Wallet Funding',
            'description': 'Add funds to your wallet',
            # 'image': 'path/to/your/logo',  # Optional: Add your logo path
            'prefill': {
                'name': request.user.username,
                'email': request.user.email,
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    


import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@login_required
def wallet_payment_success(request):
    if request.method == 'POST':
        try:
            logger.info(f"Received POST data: {request.POST}")  # Log received data
            
            params_dict = {
                'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
                'razorpay_order_id': request.POST.get('razorpay_order_id'),
                'razorpay_signature': request.POST.get('razorpay_signature')
            }

            if not all(params_dict.values()):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Missing required payment details.'
                }, status=400)

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature(params_dict)

            payment = client.payment.fetch(params_dict['razorpay_payment_id'])
            amount = payment['amount'] / 100  # Convert from paise to rupees

            wallet, created = Wallet.objects.get_or_create(user=request.user)

            wallet.balance += Decimal(str(amount))  

            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type='credit',
                description='Wallet funding via Razorpay'
            )

            return JsonResponse({
                'status': 'success',
                'message': f'₹{amount} added to your wallet successfully!'
            })

        except razorpay.errors.SignatureVerificationError:
            logger.error("Razorpay signature verification failed.")
            return JsonResponse({
                'status': 'error',
                'message': 'Payment verification failed. Please contact support if amount was deducted.'
            }, status=400)

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'An unexpected error occurred. Please try again.'
            }, status=400)

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request'
    }, status=400)

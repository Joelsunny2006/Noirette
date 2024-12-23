from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import *
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
@login_required
def wallet_view(request):
    """
    Display wallet balance and transaction history
    """
    try:
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        transactions = wallet.transactions.all().order_by('-timestamp')
        
        context = {
            'wallet': wallet,
            'transactions': transactions
        }
        return render(request, 'user_side/wallet.html', context)
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('wallet_view')  # Adjust to your home page URL name

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

@csrf_exempt
@login_required
def wallet_payment_success(request):
    """
    Handle successful wallet funding
    """
    if request.method == 'POST':
        try:
            # Verify the payment signature
            params_dict = {
                'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
                'razorpay_order_id': request.POST.get('razorpay_order_id'),
                'razorpay_signature': request.POST.get('razorpay_signature')
            }
            
            # Verify signature
            razorpay_client.utility.verify_payment_signature(params_dict)
            
            # Get payment details
            payment = razorpay_client.payment.fetch(params_dict['razorpay_payment_id'])
            amount = payment['amount'] / 100  # Convert back to rupees
            
            # Create wallet transaction
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type='credit',
                description='Wallet funding via Razorpay'
            )
            
            messages.success(request, f'₹{amount} added to your wallet successfully!')
            return JsonResponse({'status': 'success'})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)
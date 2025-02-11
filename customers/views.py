from django.shortcuts import render
from users.models import UserProfile
from django.shortcuts import redirect, get_object_or_404
from django.shortcuts import render, redirect
from admin_panel.decorator import admin_required
# Create your views here.


@admin_required
def customer(request):
    alluser = UserProfile.objects.filter(is_admin=False).order_by('id')  # Exclude admins
    return render(request, 'admin_side/customer.html', {"users": alluser})

def user_blocked(request,user_id):
    blocked_users=UserProfile.objects.get(id=user_id)
    blocked_users.is_blocked=True
    blocked_users.save()
    return redirect('customer')

def user_unblocked(request,user_id):
    unblocked_users=UserProfile.objects.get(id=user_id)
    unblocked_users.is_blocked=False
    unblocked_users.save()
    return redirect('customer')

def user_status(request, user_id):
    user = get_object_or_404(UserProfile, id=user_id)

    if request.method == 'POST':
        user.is_blocked = not user.is_blocked
        user.save()

    return redirect('customer')

# def user_delete(request,user_id):
#     deleted_users=UserProfile.objects.get(id=user_id)
#     deleted_users.delete()
#     return redirect('customer')

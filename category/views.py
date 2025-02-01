from django.shortcuts import render
from category.models import Category
from product.models import Product
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.shortcuts import render, redirect
from admin_panel.decorator import admin_required 
from django.core.paginator import Paginator

@admin_required
def category(request):
    categories = Category.objects.filter(is_deleted=False).order_by('-id')  # Show latest categories first

    # Pagination: Show 8 categories per page
    paginator = Paginator(categories, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_side/category.html', {'page_obj': page_obj})

def add_category(request):
    if request.method == 'POST':        

        name = request.POST.get('categoryName').title()
        description = request.POST.get('categoryDescription')
        status = request.POST.get('categoryStatus') == 'active'
        
        if Category.objects.filter(name=name).exists():
            messages.error(request, "A category with this name already exists.")
            return redirect('category')

        try:    
                Category.objects.create(
                    name=name, 
                    description=description, 
                    status=status
                )
            
        except Category.DoesNotExist:
            messages.error(request, 'Category not found!')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
        
            
    return redirect('category')

def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.is_deleted = True
    category.save()
    return redirect('category')


def update_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == "POST":
        name = request.POST.get("name").title()
        description = request.POST.get("description")
        if Category.objects.filter(name=name).exclude(id=category_id).exists():
            messages.error(request, "A category with this name already exists.")
            return redirect('category')
        if not name:
            return render(request, 'admin_side/update_category.html', {
                'category': category,
                'error': 'Name field is required.'
            })
        category.name = name
        category.description = description
        category.save()
        return redirect('admin_panel:category_list')
    return render(request, 'admin_side/update_category.html', {'category': category})

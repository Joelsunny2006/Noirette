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
    categories = Category.objects.all().order_by('-id')  # Show all categories # Show only active

    paginator = Paginator(categories, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_side/category.html', {'page_obj': page_obj})
@admin_required
def add_category(request):
    if request.method == 'POST':   
        print(request)     

        name = request.POST.get("name", "").strip().title()  
        description = request.POST.get("description", "").strip()
        status = request.POST.get("status", "inactive") == "active"  #
        
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
@admin_required
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    print(category.is_deleted )
    category.is_deleted = True
    print(category.is_deleted )
    category.save()
    return redirect('category')

from django.utils.text import slugify
@admin_required
def update_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip().title()  # Trim spaces and capitalize
        description = request.POST.get("description", "").strip()
        status = request.POST.get("status", "inactive") == "active"  # Convert to boolean

        if not name:
            return render(request, 'admin_side/update_category.html', {
                'category': category,
                'error': 'Name field is required.'
            })

        # Check if a different category with the same name already exists
        if Category.objects.filter(name=name).exclude(id=category.id).exists():
            messages.error(request, "A category with this name already exists.")
            return redirect('category')

        # ✅ Update existing category instead of creating a new one
        category.name = name
        category.description = description
        category.status = status  # Update the status

        # ✅ Update slug only if the name has changed
        if category.slug != slugify(name):
            category.slug = slugify(name)

        category.save()

        messages.success(request, "Category updated successfully.")
        return redirect('category')

    return render(request, 'admin_side/update_category.html', {'category': category})

@admin_required
def toggle_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.status = not category.status
    category.save()
    return redirect('category')
from django.shortcuts import render
from category.models import Category
from product.models import Product
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.shortcuts import render, redirect



def category(request):
    categories = Category.objects.filter(is_deleted=False).order_by('id')
    return render(request, 'admin_side/category.html', {'categories': categories})

def add_category(request):
    if request.method == 'POST':
        category_id = request.POST.get('categoryId')
        name = request.POST.get('categoryName')
        description = request.POST.get('categoryDescription')
        status = request.POST.get('categoryStatus') == 'active'
        
        try:
            if category_id:
                
                category = Category.objects.get(id=category_id)
                category.name = name
                category.description = description
                category.status = status
                category.save()
            else:
                
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
        name = request.POST.get("name")
        description = request.POST.get("description")
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

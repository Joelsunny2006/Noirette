from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from category.models import Category
from product.models import *
from cart.models import *
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from product.models import Product
from django.shortcuts import get_object_or_404, render
from decimal import Decimal, InvalidOperation
from admin_panel.decorator import admin_required 

def product_view(request, serial_number):
    # Get the product and related data
    product = get_object_or_404(Product, serial_number=serial_number, is_deleted=False)
    variants = product.variants.all()
    images = product.images.all()
    first_image_url = (
        images.first().image_url.url if images and images.first().image_url else None
    )

    # Add a discounted price to each variant
    for variant in variants:
        variant.discounted_price = None
        if product.offer_percentage:
            variant.discounted_price = round(
                Decimal(variant.variant_price) - 
                (Decimal(variant.variant_price) * Decimal(product.offer_percentage) / 100), 
                2
            )

    # Check if the product has variants
    total_stock = (
        sum(variant.variant_stock for variant in variants)
        if variants
        else product.stock
    )

    cart_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart_count = (
                    cart.items.aggregate(total=models.Sum("quantity"))["total"] or 0
                )
        except Cart.DoesNotExist:
            cart_count = 0

    wishlist_variant_ids = []
    if request.user.is_authenticated:
        wishlist = Wishlist.objects.filter(user=request.user).first()
        if wishlist:
            wishlist_variant_ids = [item.variant.id for item in wishlist.items.all()]

    # Pass the context to the template
    return render(
        request,
        "user_side/product.html",
        {
            "product": product,
            "variants": variants,
            "first_image_url": first_image_url,
            "images": images,
            "total_stock": total_stock,
            "cart_count": cart_count,
            "wishlist_variant_ids": wishlist_variant_ids,
        },
    )
from django.core.paginator import Paginator
@admin_required
def product_list(request):
    products = Product.objects.filter(is_deleted=False).order_by("-created")
    categories = Category.objects.filter(is_deleted=False)
    brands = Brand.objects.filter(status="active")

    # Pagination: Show 8 products per page
    paginator = Paginator(products, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "admin_side/products.html",
        {"page_obj": page_obj, "categories": categories, "brands": brands},
    )

def add_product(request):
    if request.method == "POST":
        try:
            # Basic validation
            name = request.POST.get("product_name").title()

            if Product.objects.filter(name=name).exclude(id=product).exists():
                return JsonResponse({"success": False, "message": "A product with this name already exists."})

            if not name:
                return JsonResponse({"success": False, "message": "Product name is required"})

            description = request.POST.get("product_description")
            category_id = request.POST.get("product_category")
            brand_id = request.POST.get("product_brand")
            offer_percentage = request.POST.get("offer_price_percentage", '0')

            try:
                offer_percentage = Decimal(offer_percentage)
                if offer_percentage < 0 or offer_percentage > 100:
                    return JsonResponse({"success": False, "message": "Offer percentage must be between 0 and 100"})
                
                category = Category.objects.get(id=category_id)
                brand = Brand.objects.get(id=brand_id)
            except InvalidOperation:
                return JsonResponse({"success": False, "message": "Invalid offer percentage"})
            except (Category.DoesNotExist, Brand.DoesNotExist):
                return JsonResponse({"success": False, "message": "Invalid category or brand selected"})

            # Create product
            product = Product.objects.create(
                name=name,
                description=description,
                category=category,
                brand=brand,
                offer_percentage=offer_percentage
            )

            # Handle variants
            variant_names = request.POST.getlist("variant_name[]")
            variant_prices = request.POST.getlist("variant_price[]")
            variant_stocks = request.POST.getlist("variant_stock[]")

            if not variant_names:
                product.delete()
                return JsonResponse({"success": False, "message": "At least one variant is required"})

            try:
                for name, price, stock in zip(variant_names, variant_prices, variant_stocks):
                    if not name or not price or not stock:
                        raise ValueError("All variant fields are required")
                        
                    price = Decimal(price)
                    stock = int(stock)
                    
                    if price <= 0:
                        raise ValueError("Price must be greater than 0")
                    if stock < 0:
                        raise ValueError("Stock cannot be negative")
                        
                    Variant.objects.create(
                        product=product,
                        variant_name=name,
                        variant_price=price,
                        variant_stock=stock
                    )
            except (ValueError, InvalidOperation) as e:
                product.delete()
                return JsonResponse({"success": False, "message": f"Invalid variant data: {str(e)}"})

            # Handle images
            images = request.FILES.getlist("product_images")
            if not images:
                product.delete()
                return JsonResponse({"success": False, "message": "At least one product image is required"})

            if len(images) > 5:
                product.delete()
                return JsonResponse({"success": False, "message": "Maximum 5 images allowed"})

            for image in images:
                ProductImage.objects.create(product=product, image_url=image)

            return JsonResponse({"success": True, "message": "Product added successfully"})
            
        except Exception as e:
            return JsonResponse({"success": False, "message": f"An error occurred: {str(e)}"})

    return JsonResponse({"success": False, "message": "Invalid request method"})


def update_product(request, product_id):
    categories = Category.objects.filter(status=True)  # ✅ Fixed query
    brands = Brand.objects.filter(status="active")

    try:
        product = Product.objects.get(serial_number=product_id)
    except Product.DoesNotExist:
        return JsonResponse({"success": False, "message": "Product not found"})
    
    print(request.POST)

    if request.method == "POST":
        try:
            # Update basic info
            name = request.POST.get("product_name").title()

            if Product.objects.filter(name=name).exclude(id=product_id).exists():
                return JsonResponse({"success": False, "message": "A product with this name already exists."})

            product.description = request.POST.get("description")

            # ✅ Ensure Category Exists
            category_id = request.POST.get("category")
            if category_id:
                try:
                    product.category = Category.objects.get(id=category_id)
                except Category.DoesNotExist:
                    return JsonResponse({"success": False, "message": "Invalid category selected"})

            # ✅ Validate Offer Percentage
            offer_percentage = request.POST.get("offer_price_percentage", '0')
            try:
                offer_percentage = Decimal(offer_percentage)
                if not (0 <= offer_percentage <= 100):
                    return JsonResponse({"success": False, "message": "Offer percentage must be between 0 and 100"})
                product.offer_percentage = offer_percentage
            except InvalidOperation:
                return JsonResponse({"success": False, "message": "Invalid offer percentage"})

            product.save()

            # ✅ Handle Variants
            variant_ids = request.POST.getlist("variant_id[]")
            variant_names = request.POST.getlist("variant_name[]")
            variant_prices = request.POST.getlist("variant_price[]")
            variant_stocks = request.POST.getlist("variant_stock[]")



            print(variant_ids)
            print(variant_names)
            print(variant_prices)
            print(variant_stocks)

            existing_variants = set(product.variants.values_list('id', flat=True))
            updated_variants = set()

            for i in range(len(variant_names)):
                try:
                    name = variant_names[i]
                    price = Decimal(variant_prices[i])
                    stock = int(variant_stocks[i])
                    variant_id = variant_ids[i] if i < len(variant_ids) else None

                    if price <= 0:
                        raise ValueError("Price must be greater than 0")
                    if stock < 0:
                        raise ValueError("Stock cannot be negative")

                    if variant_id and variant_id.isdigit():
                        variant_id = int(variant_id)
                        variant = Variant.objects.get(id=variant_id, product=product)
                        variant.variant_name = name
                        variant.variant_price = price
                        variant.variant_stock = stock
                        variant.save()
                        updated_variants.add(variant_id)
                    else:
                        variant = Variant.objects.create(
                            product=product,
                            variant_name=name,
                            variant_price=price,
                            variant_stock=stock
                        )
                        updated_variants.add(variant.id)

                except (Variant.DoesNotExist, ValueError, InvalidOperation) as e:
                    return JsonResponse({"success": False, "message": f"Error updating variant: {str(e)}"})

            # ✅ Delete unused variants
            variants_to_delete = existing_variants - updated_variants
            Variant.objects.filter(id__in=variants_to_delete).delete()

            # ✅ Handle Image Upload
            new_images = request.FILES.getlist("product_images")
            current_images = product.images.count()

            if current_images + len(new_images) > 5:
                return JsonResponse({"success": False, "message": "Maximum 5 images allowed"})

            for image in new_images:
                ProductImage.objects.create(product=product, image_url=image)

            return JsonResponse({"success": True, "message": "Product updated successfully"})

        except Exception as e:
            return JsonResponse({"success": False, "message": f"An error occurred: {str(e)}"})

    # ✅ Return Product, Categories, and Brands in GET Request
    return render(request, "admin_side/edit_product.html", {
        "product": product,
        "brands": brands,
        "categories": categories
    })
def delete_product(request, product_id):
    try:
        product = Product.objects.get(serial_number=product_id)
        product.is_deleted = True
        product.save()
        messages.success(request, "Product deleted successfully.")
    except Product.DoesNotExist:
        messages.error(request, "Product not found.")
    return redirect("product_list")

from django.views.decorators.http import require_POST
@require_POST
def remove_product_image(request, image_id):
    try:
        # Get the image object
        image = get_object_or_404(ProductImage, id=image_id)
        
        # Delete the image file from storage
        if image.image_url:
            image.image_url.delete()
        
        # Delete the image record from database
        image.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Image removed successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@admin_required
def brand_list(request):
    brands = Brand.objects.all().order_by('-id')  # Show latest brands first
    return render(request, "admin_side/brand.html", {"brands": brands})

def add_brand(request):
    if request.method == "POST":
        brand_id = request.POST.get("brandId")
        name = request.POST.get("brandName").title()
        status = request.POST.get("brandStatus")
        
        if Brand.objects.filter(name=name).exclude(id=brand_id).exists():
            messages.error(request, "A brand with this name already exists.")
            return redirect('brand')

        try:
            if brand_id:
                brand = Brand.objects.get(id=brand_id)
                brand.name = name
                brand.status = status
                brand.save()
                messages.success(request, "Brand updated successfully.")
            else:
                if Brand.objects.filter(name=name).exists():
                    messages.error(request, "A brand with this name already exists.")
                    return redirect('brand')
                else:
                    Brand.objects.create(name=name, status=status)
                    messages.success(request, "Brand added successfully.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return redirect("brand")

    brands = Brand.objects.all()
    return render(request, "admin_side/brand.html", {"brands": brands})


def delete_brand(request, brand_id):
    try:
        brand = get_object_or_404(Brand, id=brand_id)
        brand.delete()
        messages.success(request, "Brand deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting brand: {str(e)}")
    return redirect("brand")


def edit_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)

    if request.method == "POST":
        name = request.POST.get("brandName").title()
        status = request.POST.get("brandStatus")
        if Brand.objects.filter(name=name).exclude(id=brand_id).exists():
                messages.error(request, "A brand with this name already exists.")
                return redirect('brand')
        try:
            existing_brand = (
                Brand.objects.filter(name=name).exclude(id=brand_id).first()
            )
            if existing_brand:
                messages.error(request, "A brand with this name already exists.")
                return redirect("brand")
            brand.name = name
            brand.status = status
            brand.save()
            messages.success(request, "Brand updated successfully.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return redirect("brand")

    brands = Brand.objects.all()
    return render(
        request, "admin_side/brand.html", {"brands": brands, "edit_brand": brand}
    )

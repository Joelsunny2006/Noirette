# views.py
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from datetime import datetime, timedelta
import pandas as pd
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from order.models import *
from django.shortcuts import render
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDate, ExtractMonth
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from django.contrib import messages
from admin_panel.decorator import admin_required 
from django.core.paginator import Paginator

@admin_required
def sales_report(request):
    # Initialize default queryset
    orders = Order.objects.all().order_by('-created_at')  # Newest orders first

    print(orders)
    
    # Initialize date filter variables
    start_date = None
    end_date = None
    filter_applied = False

    # Handle custom date filter (POST request)
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        if start_date_str and end_date_str:
            try:
                # Parse dates and set time to start/end of day
                start_date = timezone.make_aware(
                    datetime.strptime(start_date_str, '%Y-%m-%d').replace(
                        hour=0, minute=0, second=0
                    )
                )
                end_date = timezone.make_aware(
                    datetime.strptime(end_date_str, '%Y-%m-%d').replace(
                        hour=23, minute=59, second=59
                    )
                )
                
                orders = orders.filter(
                    created_at__gte=start_date,
                    created_at__lte=end_date
                )
                filter_applied = True
            except ValueError:
                # Add error message if date parsing fails
                messages.error(request, 'Invalid date format. Please use YYYY-MM-DD format.')

    # Handle weekly/monthly filters (GET request)
    filter_type = request.GET.get('filter')
    if filter_type and not filter_applied:  # Only apply if no custom date filter
        today = timezone.now()
        if filter_type == 'weekly':
            start_date = today - timedelta(days=7)
            orders = orders.filter(created_at__gte=start_date)
            filter_applied = True
        elif filter_type == 'monthly':
            start_date = today.replace(day=1, hour=0, minute=0, second=0)
            orders = orders.filter(created_at__gte=start_date)
            filter_applied = True

    # Pagination
    paginator = Paginator(orders, 10)  # 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calculate summary statistics
    summary_stats = orders.aggregate(
        total_orders=Count('id'),
        total_order_amount=Sum('total_price'),
        total_discount=Sum('coupon_discount', default=0)
    )
    
    # Prepare context with default values for empty queryset
    context = {
        'page_obj': page_obj,  # Changed from 'orders' to 'page_obj'
        'total_orders': summary_stats['total_orders'] or 0,
        'total_order_amount': summary_stats['total_order_amount'] or 0,
        'total_discount': summary_stats['total_discount'] or 0,
        'filter_type': filter_type,
        'start_date': start_date.date().isoformat() if start_date else '',
        'end_date': end_date.date().isoformat() if end_date else '',
        'filter_applied': filter_applied
    }

    return render(request, 'admin_side/sales_report.html', context)
@admin_required
def get_date_range(report_type, start_date=None, end_date=None):
    """Helper function to calculate date ranges based on report type"""
    today = datetime.now().date()
    
    if report_type == 'daily':
        return today, today
    elif report_type == 'weekly':
        start_date = today - timedelta(days=7)
        return start_date, today
    elif report_type == 'monthly':
        start_date = today.replace(day=1)
        return start_date, today
    elif report_type == 'yearly':
        start_date = today.replace(month=1, day=1)
        return start_date, today
    elif report_type == 'custom' and start_date and end_date:
        return start_date, end_date
    return today, today
@admin_required
@require_http_methods(["GET"])
def sales_report_api(request):
    try:
        report_type = request.GET.get('report_type', 'monthly')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        if report_type == 'custom' and start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return JsonResponse({
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=400)
        else:
            start_date, end_date = get_date_range(report_type)

        orders = Order.objects.filter(
            created_at__date__range=[start_date, end_date],
            status__in=['Completed', 'Shipped']
        )

        # Calculate metrics
        total_sales = orders.aggregate(
            total=Sum('total_price')
        )['total'] or Decimal('0')
        
        total_orders = orders.count()
        total_discount = orders.aggregate(
            total_discount=Sum('coupon_discount')
        )['total_discount'] or Decimal('0')

        # Daily breakdown
        daily_orders = orders.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            sales_count=Count('id'),
            total_amount=Sum('total_price'),
            discount_amount=Sum('coupon_discount'),
            net_amount=ExpressionWrapper(
                Sum('total_price') - Sum(F('coupon_discount')),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).order_by('date')

        order_details = [{
            'date': item['date'].strftime('%Y-%m-%d'),
            'sales_count': item['sales_count'],
            'total_amount': float(item['total_amount']),
            'discount_amount': float(item['discount_amount'] or 0),
            'net_amount': float(item['net_amount'] or 0)
        } for item in daily_orders]

        return JsonResponse({
            'total_sales': float(total_sales),
            'total_orders': total_orders,
            'total_discount': float(total_discount),
            'order_details': order_details,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@admin_required
@require_http_methods(["GET"])
def download_sales_report(request):
    try:
        report_type = request.GET.get('report_type', 'monthly')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        download_type = request.GET.get('download_type', 'excel')

        # Get date range
        if report_type == 'custom' and start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return JsonResponse({
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=400)
        else:
            start_date, end_date = get_date_range(report_type)

        # Get orders
        orders = Order.objects.filter(
            created_at__date__range=[start_date, end_date],
            status__in=['Completed', 'Shipped']
        )

        # Prepare data
        daily_data = orders.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            sales_count=Count('id'),
            total_amount=Sum('total_price'),
            discount_amount=Sum('coupon_discount'),
            net_amount=ExpressionWrapper(
                Sum('total_price') - Sum(F('coupon_discount')),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).order_by('date')

        # Format data for report
        report_data = []
        totals = {
            'sales_count': 0,
            'total_amount': Decimal('0'),
            'discount_amount': Decimal('0'),
            'net_amount': Decimal('0')
        }

        for item in daily_data:
            row_data = {
                'Date': item['date'].strftime('%Y-%m-%d'),
                'Orders': item['sales_count'],
                'Revenue': float(item['total_amount']),
                'Discounts': float(item['discount_amount'] or 0),
                'Net Amount': float(item['net_amount'] or 0)
            }
            report_data.append(row_data)
            
            # Update totals
            totals['sales_count'] += item['sales_count']
            totals['total_amount'] += item['total_amount']
            totals['discount_amount'] += item['discount_amount'] or 0
            totals['net_amount'] += item['net_amount'] or 0

        # Add summary row
        report_data.append({
            'Date': 'Total',
            'Orders': totals['sales_count'],
            'Revenue': float(totals['total_amount']),
            'Discounts': float(totals['discount_amount']),
            'Net Amount': float(totals['net_amount'])
        })

        if download_type == 'excel':
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=sales_report_{start_date}_{end_date}.xlsx'

            df = pd.DataFrame(report_data)
            
            # Create Excel writer with xlsxwriter engine
            with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Sales Report')
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Sales Report']
                
                # Add formats
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#0066cc',
                    'color': 'white'
                })
                
                # Format currency columns
                money_format = workbook.add_format({'num_format': '$#,##0.00'})
                
                # Apply formats
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    if value in ['Revenue', 'Discounts', 'Net Amount']:
                        worksheet.set_column(col_num, col_num, 15, money_format)
                    else:
                        worksheet.set_column(col_num, col_num, 15)

            return response
        
        elif download_type == 'pdf':
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename=sales_report_{start_date}_{end_date}.pdf'

            # Create PDF
            doc = SimpleDocTemplate(response, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()

            # Add title
            elements.append(Paragraph(f"Sales Report ({start_date} to {end_date})", styles['Heading1']))
            elements.append(Spacer(1, 20))

            # Create table data
            table_data = [['Date', 'Orders', 'Revenue', 'Discounts', 'Net Amount']]
            for row in report_data:
                table_data.append([
                    row['Date'],
                    str(row['Orders']),
                    f"${row['Revenue']:,.2f}",
                    f"${row['Discounts']:,.2f}",
                    f"${row['Net Amount']:,.2f}"
                ])

            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, -1), (-1, -1), colors.grey),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))

            elements.append(table)
            doc.build(elements)
            return response

        return JsonResponse({'error': 'Invalid download type'}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

from datetime import datetime, timedelta
from django.utils import timezone
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
@admin_required
def salesanalytics(request):
    filter_type = request.GET.get('filter', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    today = timezone.now()

    # Get all orders (for displaying all orders)
    if filter_type == 'weekly':
        start_date = today - timedelta(days=7)
        orders = Order.objects.filter(created_at__gte=start_date)
    elif filter_type == 'monthly':
        orders = Order.objects.filter(created_at__month=today.month, created_at__year=today.year)
    elif start_date and end_date:
        start_date = timezone.make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
        end_date = timezone.make_aware(datetime.strptime(end_date, "%Y-%m-%d"))
        orders = Order.objects.filter(created_at__range=[start_date, end_date])
    else:
        orders = Order.objects.all()  # ✅ Show all orders

    # ✅ Get only Completed Orders for Revenue & Discount Calculation
    completed_orders = orders.filter(status='Completed')

    # ✅ Explicitly order the queryset
    orders = orders.order_by('-created_at')

    # Calculate total values
    total_orders = orders.count()  # ✅ Count all orders
    total_order_amount = completed_orders.aggregate(total_amount=Sum('total_price'))['total_amount'] or 0  # ✅ Only from Completed orders
    total_discount = completed_orders.aggregate(total_discount=Sum('coupon_discount'))['total_discount'] or 0  # ✅ Only from Completed orders

    payment_methods = orders.values('payment_method').annotate(count=Sum('total_price')).order_by('payment_method')

    # Pagination
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'orders': orders,
        'total_orders': total_orders,  # ✅ Show count of all orders
        'total_order_amount': total_order_amount,  # ✅ Only Completed Orders Revenue
        'total_discount': total_discount,  # ✅ Only Completed Orders Discount
        'payment_methods': payment_methods,
    }

    return render(request, 'admin_side/salesanalytics.html', context)



# def salesanalytics(request):
#     try:
#         # Get default date range (last 30 days)
#         end_date = timezone.now().date()
#         start_date = end_date - timedelta(days=30)

#         # Get completed/shipped orders for the current period
#         orders = Order.objects.filter(
#             created_at__date__range=[start_date, end_date],
#             status__in=['Completed', 'Shipped']
#         )

#         # Previous period orders for comparison
#         previous_start = start_date - timedelta(days=30)
#         previous_orders = Order.objects.filter(
#             created_at__date__range=[previous_start, start_date - timedelta(days=1)],
#             status__in=['Completed', 'Shipped']
#         )

#         # Calculate current period metrics
#         total_revenue = orders.aggregate(
#             total=Sum('total_price')
#         )['total'] or Decimal('0.00')

#         total_orders = orders.count()
#         total_discount = orders.aggregate(
#             total=Sum('coupon_discount')
#         )['total'] or Decimal('0.00')

#         # Calculate previous period metrics for comparison
#         previous_revenue = previous_orders.aggregate(
#             total=Sum('total_price')
#         )['total'] or Decimal('0.00')

#         # Calculate revenue change percentage
#         revenue_change_percentage = (
#             ((total_revenue - previous_revenue) / previous_revenue) * 100
#             if previous_revenue > 0 else 0
#         )

#         # Daily breakdown with proper annotations
#         report_data = orders.annotate(
#             date=TruncDate('created_at')
#         ).values('date').annotate(
#             sales_count=Count('id'),
#             total_amount=Sum('total_price'),
#             discount_amount=Sum('coupon_discount'),
#             net_amount=ExpressionWrapper(
#                 Sum('total_price') - Sum(F('coupon_discount')),
#                 output_field=DecimalField(max_digits=10, decimal_places=2)
#             )
#         ).order_by('date')

#         # Convert QuerySet to list for template rendering
#         report_data = list(report_data)

#         # Calculate net amount
#         net_amount = total_revenue - total_discount

#         context = {
#             'total_revenue': total_revenue,
#             'total_orders': total_orders,
#             'total_discount': total_discount,
#             'net_amount': net_amount,
#             'revenue_change_percentage': revenue_change_percentage,
#             'report_data': report_data,
#             'start_date': start_date.strftime('%Y-%m-%d'),
#             'end_date': end_date.strftime('%Y-%m-%d'),
#             'page_title': 'Sales Analytics',
#         }

#         return render(request, 'admin_side/salesanalytics.html', context)

#     except Exception as e:
#         print(f"Error in salesanalytics view: {str(e)}")
#         return render(request, 'admin_side/salesanalytics.html', {
#             'error_message': str(e),
#             'total_revenue': Decimal('0.00'),
#             'total_orders': 0,
#             'total_discount': Decimal('0.00'),
#             'net_amount': Decimal('0.00'),
#             'revenue_change_percentage': 0,
#             'report_data': [],
#         })
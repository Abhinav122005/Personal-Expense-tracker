<<<<<<< HEAD
# tracker/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
import json
from decimal import Decimal
import csv
from datetime import datetime
from django.db.models import Sum, Max
from django.utils import timezone
from django.core.paginator import Paginator
import openpyxl

from .models import Expense, UserBudget

# ----------------------------------------------------
# Authentication Views
# ----------------------------------------------------
def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

# ----------------------------------------------------
# Main Page View
# ----------------------------------------------------
@login_required(login_url='login')
def index(request):
    """Renders the main expense tracker HTML page."""
    return render(request, 'index.html')

# ----------------------------------------------------
# Data API
# ----------------------------------------------------
@login_required(login_url='login')
@require_http_methods(["GET", "POST", "DELETE"]) 
def api_expenses(request):
    
    if request.method == 'GET':
        expenses = Expense.objects.filter(user=request.user).order_by('-created_at')
        
        # Filtering
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        category = request.GET.get('category')
        
        if start_date:
            try:
                dt_start = datetime.strptime(start_date, '%Y-%m-%d').date()
                dt_start = datetime.combine(dt_start, datetime.min.time())
                expenses = expenses.filter(created_at__gte=timezone.make_aware(dt_start))
            except ValueError:
                pass
                
        if end_date:
            try:
                dt_end = datetime.strptime(end_date, '%Y-%m-%d').date()
                dt_end = datetime.combine(dt_end, datetime.max.time())
                expenses = expenses.filter(created_at__lte=timezone.make_aware(dt_end))
            except ValueError:
                pass
                
        if category and category != 'All':
            expenses = expenses.filter(category=category)
            
        # Pagination
        page_number = request.GET.get('page', 1)
        paginator = Paginator(expenses, 10) # 10 expenses per page
        page_obj = paginator.get_page(page_number)
        
        data = {
            'expenses': list(page_obj.object_list.values('id', 'description', 'amount', 'category', 'created_at')),
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages
        }
        return JsonResponse(data, safe=False)
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount_decimal = Decimal(data['amount']) 
            
            created_at = timezone.now()
            if 'date' in data and data['date']:
                try:
                    # date from frontend input type="date" is YYYY-MM-DD
                    parsed_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                    created_at = datetime.combine(parsed_date, datetime.min.time())
                    created_at = timezone.make_aware(created_at)
                except ValueError:
                    pass
            
            new_expense = Expense.objects.create(
                user=request.user,
                description=data['description'],
                amount=amount_decimal,
                category=data['category'],
                created_at=created_at
            )
            
            return JsonResponse({
                'id': new_expense.id,
                'description': new_expense.description,
                'amount': str(new_expense.amount), 
                'category': new_expense.category,
                'date': new_expense.created_at.strftime('%Y-%m-%d')
            }, status=201) 
            
        except (json.JSONDecodeError, KeyError):
             return JsonResponse({'error': 'Invalid data format or missing fields'}, status=400)
        except Exception as e:
            print(f"Error creating expense: {e}")
            return JsonResponse({'error': 'Internal server error during save.'}, status=500)

    elif request.method == 'DELETE':
        try:
            Expense.objects.filter(user=request.user).delete()
            return JsonResponse({}, status=204) 
        except Exception as e:
            return JsonResponse({'error': f'Database error: {e}'}, status=500)

@login_required(login_url='login')
@require_http_methods(["DELETE", "PUT"])
def api_expense_detail(request, expense_id):
    try:
        expense = Expense.objects.get(id=expense_id, user=request.user)
    except Expense.DoesNotExist:
        return JsonResponse({'error': 'Expense not found'}, status=404)
        
    if request.method == 'DELETE':
        expense.delete()
        return JsonResponse({}, status=204)
        
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            if 'description' in data:
                expense.description = data['description']
            if 'amount' in data:
                expense.amount = Decimal(data['amount'])
            if 'category' in data:
                expense.category = data['category']
            if 'date' in data and data['date']:
                try:
                    parsed_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                    created_at = datetime.combine(parsed_date, datetime.min.time())
                    expense.created_at = timezone.make_aware(created_at)
                except ValueError:
                    pass
                    
            expense.save()
            return JsonResponse({
                'id': expense.id,
                'description': expense.description,
                'amount': str(expense.amount),
                'category': expense.category,
                'date': expense.created_at.strftime('%Y-%m-%d')
            })
        except Exception as e:
             return JsonResponse({'error': f'Update error: {e}'}, status=400)

# ----------------------------------------------------
# Budget API
# ----------------------------------------------------
@login_required(login_url='login')
@require_http_methods(["GET", "POST"])
def api_budget(request):
    budget, created = UserBudget.objects.get_or_create(user=request.user)
    
    if request.method == 'GET':
        return JsonResponse({'amount': str(budget.amount)})
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            budget.amount = Decimal(data['amount'])
            budget.save()
            return JsonResponse({'amount': str(budget.amount)}, status=200)
        except Exception as e:
            return JsonResponse({'error': f'Invalid data: {e}'}, status=400)

# ----------------------------------------------------
# Dashboard Analytics API
# ----------------------------------------------------
@login_required(login_url='login')
@require_http_methods(["GET"])
def api_analytics(request):
    expenses = Expense.objects.filter(user=request.user)
    budget, _ = UserBudget.objects.get_or_create(user=request.user)
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        try:
            dt_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            dt_start = datetime.combine(dt_start, datetime.min.time())
            expenses = expenses.filter(created_at__gte=timezone.make_aware(dt_start))
        except ValueError:
            pass
            
    if end_date:
        try:
            dt_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            dt_end = datetime.combine(dt_end, datetime.max.time())
            expenses = expenses.filter(created_at__lte=timezone.make_aware(dt_end))
        except ValueError:
            pass
    
    # Total Expenses (Filtered Period)
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    # Category-wise Expenses
    categories = ['Food', 'Housing', 'Transport', 'Entertainment', 'Other']
    category_data = {}
    for cat in categories:
        cat_total = expenses.filter(category=cat).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        category_data[cat] = float(cat_total)
        
    # Highest Spending Category
    highest_category = "None"
    highest_amount = Decimal('0.00')
    for cat, amount in category_data.items():
        if Decimal(str(amount)) > highest_amount:
            highest_amount = Decimal(str(amount))
            highest_category = cat
            
    # Budget tracking (compared against the filtered period's total)
    budget_amount = budget.amount
    budget_percent = 0
    if budget_amount > 0:
        budget_percent = min(100, int((total_expenses / budget_amount) * 100))

    data = {
        'total_expenses': str(total_expenses),
        'monthly_expenses': str(total_expenses), # Removed month specific, matching period total
        'category_data': category_data,
        'highest_category': highest_category,
        'budget_amount': str(budget_amount),
        'budget_percent': budget_percent
    }
    return JsonResponse(data)

# ----------------------------------------------------
# Export Feature Views
# ----------------------------------------------------
@login_required(login_url='login')
def export_csv(request):
    expenses = Expense.objects.filter(user=request.user).order_by('-created_at')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="expenses_{request.user.username}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Description', 'Amount', 'Category', 'Date'])
    
    for expense in expenses:
        writer.writerow([expense.description, expense.amount, expense.category, expense.created_at.strftime("%Y-%m-%d")])
        
    return response

@login_required(login_url='login')
def export_excel(request):
    expenses = Expense.objects.filter(user=request.user).order_by('-created_at')
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="expenses_{request.user.username}.xlsx"'
    
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = 'Expenses'
    
    columns = ['Description', 'Amount', 'Category', 'Date']
    worksheet.append(columns)
    
    for expense in expenses:
        worksheet.append([
            expense.description,
            float(expense.amount), 
            expense.category,
            expense.created_at.strftime("%Y-%m-%d")
        ])
        
    workbook.save(response)
    return response
=======
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from decimal import Decimal

from .models import Expense 

def index(request):
    """Renders the main expense tracker HTML page."""
    return render(request, 'index.html')

# API View to handle data operations (GET, POST, DELETE)
@require_http_methods(["GET", "POST", "DELETE"]) 
def api_expenses(request):
    
    # ----------------------------------------------------
    # GET: Retrieve all expenses
    # ----------------------------------------------------
    if request.method == 'GET':
        expenses = Expense.objects.all().order_by('-created_at')
        
        # NOTE: .values() is used here for simple serialization.
        data = list(expenses.values('description', 'amount', 'category'))
        return JsonResponse(data, safe=False)
        
    # ----------------------------------------------------
    # POST: Add a new expense
    # ----------------------------------------------------
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Use Decimal conversion to avoid float precision issues in Python
            amount_decimal = Decimal(data['amount']) 
            
            new_expense = Expense.objects.create(
                description=data['description'],
                amount=amount_decimal,
                category=data['category']
            )
            
            # Return the created object's data with amount converted back to a string
            # to ensure JSON serialization is exact.
            return JsonResponse({
                'description': new_expense.description,
                'amount': str(new_expense.amount), # Convert Decimal to str for JSON
                'category': new_expense.category
            }, status=201) 
            
        except (json.JSONDecodeError, KeyError):
             return JsonResponse({'error': 'Invalid data format or missing fields'}, status=400)
        except Exception as e:
            # Logs the error to your terminal
            print(f"Error creating expense: {e}")
            return JsonResponse({'error': 'Internal server error during save.'}, status=500)

    # ----------------------------------------------------
    # DELETE: Clear all expenses
    # ----------------------------------------------------
    elif request.method == 'DELETE':
        try:
            # Delete all records
            Expense.objects.all().delete()
            return JsonResponse({}, status=204) # 204 No Content is standard for DELETE
        except Exception as e:

            return JsonResponse({'error': f'Database error: {e}'}, status=500)
>>>>>>> 0c20d9b1918814c07bd3706f96abf9192c1cfcfb

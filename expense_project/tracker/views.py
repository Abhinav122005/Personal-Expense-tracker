# tracker/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.urls import reverse
from decimal import Decimal
import csv
from datetime import datetime
from django.db.models import Sum
from django.utils import timezone
from django.core.paginator import Paginator
import openpyxl
import json

from .models import Expense, UserBudget

from django import forms
from django.contrib.auth.models import User

# ----------------------------------------------------
# Custom Forms
# ----------------------------------------------------
class EmailRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email Address")
    
    class Meta:
        model = User
        fields = ("email",)
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email Address", widget=forms.EmailInput(attrs={'autofocus': True}))


# ----------------------------------------------------
# Authentication Views
# ----------------------------------------------------
def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = EmailRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('index')
    else:
        form = EmailRegistrationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = EmailAuthenticationForm(data=request.POST, request=request)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('index')
    else:
        form = EmailAuthenticationForm(request=request)
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

# ----------------------------------------------------
# Main Page View
# ----------------------------------------------------
@login_required(login_url='login')
def index(request):
    budget, _ = UserBudget.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'toggle_theme':
            current = request.session.get('theme', 'light')
            request.session['theme'] = 'dark' if current == 'light' else 'light'
            return redirect(request.META.get('HTTP_REFERER', 'index'))
            
        elif action == 'set_budget':
            amount = request.POST.get('budget_amount', '0')
            try:
                budget.amount = Decimal(amount)
                budget.save()
                messages.success(request, "Budget updated successfully!")
            except Exception:
                messages.error(request, "Invalid budget amount.")
            return redirect(request.META.get('HTTP_REFERER', 'index'))
            
        elif action == 'clear_all':
            Expense.objects.filter(user=request.user).delete()
            messages.success(request, "All expenses cleared.")
            return redirect('index')
            
        elif action == 'delete_expense':
            exp_id = request.POST.get('expense_id')
            exp = get_object_or_404(Expense, id=exp_id, user=request.user)
            exp.delete()
            messages.success(request, "Expense deleted.")
            return redirect(request.META.get('HTTP_REFERER', 'index'))
            
        elif action == 'add_expense' or action == 'edit_expense':
            description = request.POST.get('description')
            amount_str = request.POST.get('amount')
            category = request.POST.get('category')
            date_str = request.POST.get('expense-date')
            
            try:
                amount_decimal = Decimal(amount_str)
                if amount_decimal <= 0:
                    raise ValueError("Amount must be positive.")
                
                parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                created_at = timezone.make_aware(datetime.combine(parsed_date, datetime.min.time()))
                
                if action == 'edit_expense':
                    exp_id = request.POST.get('expense_id')
                    exp = get_object_or_404(Expense, id=exp_id, user=request.user)
                    exp.description = description
                    exp.amount = amount_decimal
                    exp.category = category
                    exp.created_at = created_at
                    exp.save()
                    messages.success(request, "Expense updated successfully!")
                else:
                    Expense.objects.create(
                        user=request.user,
                        description=description,
                        amount=amount_decimal,
                        category=category,
                        created_at=created_at
                    )
                    messages.success(request, "Expense added successfully!")
            except Exception as e:
                messages.error(request, f"Error saving expense: {str(e)}")
                
            # Clear GET parameters after form submission to prevent resubmission loops
            return redirect('index')

    # GET Request Processing
    expenses = Expense.objects.filter(user=request.user).order_by('-created_at')
    
    # Check for Edit Mode
    edit_id = request.GET.get('edit_id')
    edit_expense = None
    if edit_id:
        try:
            edit_expense = Expense.objects.get(id=edit_id, user=request.user)
        except Expense.DoesNotExist:
            pass

    # Filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category_filter = request.GET.get('category')
    
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
            
    if category_filter and category_filter != 'All':
        expenses = expenses.filter(category=category_filter)
        
    # Analytics (On filtered subset)
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    categories = ['Food', 'Housing', 'Transport', 'Entertainment', 'Other']
    category_data = {}
    for cat in categories:
        cat_total = expenses.filter(category=cat).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        category_data[cat] = float(cat_total)
        
    highest_category = "None"
    highest_amount = Decimal('0.00')
    for cat, amount in category_data.items():
        if Decimal(str(amount)) > highest_amount:
            highest_amount = Decimal(str(amount))
            highest_category = cat
            
    # Budget Tracking
    budget_amount = budget.amount
    budget_percent = 0
    if budget_amount > 0:
        budget_percent = min(100, int((total_expenses / budget_amount) * 100))
        
    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(expenses, 10)
    page_obj = paginator.get_page(page_number)
    
    # Query String for pagination links (to preserve filters)
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    
    context = {
        'page_obj': page_obj,
        'edit_expense': edit_expense,
        'total_expenses': total_expenses,
        'highest_category': highest_category,
        'budget_amount': budget_amount,
        'budget_percent': budget_percent,
        'category_data_json': json.dumps(category_data),
        
        # Preserve filters in context for inputs
        'start_date': start_date,
        'end_date': end_date,
        'category_filter': category_filter,
        'query_string': query_params.urlencode(),
        
        # Pass theme
        'theme': request.session.get('theme', 'light'),
        'today': timezone.now().strftime('%Y-%m-%d')
    }
    
    return render(request, 'index.html', context)

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

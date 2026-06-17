# tracker/views.py
from django.conf import settings
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

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from .models import Expense, UserBudget

User = get_user_model()

# ----------------------------------------------------
# Custom Forms
# ----------------------------------------------------
class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email Address", widget=forms.EmailInput(attrs={'autofocus': True}))


# ----------------------------------------------------
# Profile View
# ----------------------------------------------------
@login_required(login_url='login')
def profile_view(request):
    user = request.user
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_email':
            new_email = request.POST.get('email')
            if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                messages.error(request, "This email is already in use by another account.")
            else:
                user.email = new_email
                user.save()
                messages.success(request, "Email updated successfully!")
            return redirect('profile')
            
        elif action == 'update_password':
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Keep the user logged in
                messages.success(request, "Password updated successfully!")
                return redirect('profile')
            else:
                for field, errors in password_form.errors.items():
                    for error in errors:
                        messages.error(request, error)
    else:
        password_form = PasswordChangeForm(user)
        
    return render(request, 'profile.html', {
        'password_form': password_form,
        'theme': request.session.get('theme', 'light')
    })


# ----------------------------------------------------
# Authentication Views
# ----------------------------------------------------
import random
from django.core.mail import send_mail
from .serializers import RegistrationSerializer, OTPVerificationSerializer
from .models import EmailOTP
import uuid

def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        serializer = RegistrationSerializer(data=request.POST)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            # Generate 6-digit OTP
            otp_code = str(random.randint(100000, 999999))
            
            # Save OTP to database (overwrite if exists)
            EmailOTP.objects.update_or_create(email=email, defaults={'otp_code': otp_code})
            
            # Send OTP Email
            try:
                send_mail(
                    'Your Expense Tracker OTP Code',
                    f'Your verification code is: {otp_code}',
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
                )
            except Exception as e:
                messages.error(request, f"Failed to send email. Error: {str(e)}")
                print(f"EMAIL SEND ERROR: {e}")
            
            # Save registration data in session
            request.session['registration_data'] = serializer.validated_data
            messages.success(request, f"OTP sent to {email}. Please verify.")
            return redirect('verify_otp')
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return render(request, 'register.html')

def verify_otp_view(request):
    if request.user.is_authenticated:
        return redirect('index')
        
    if 'registration_data' not in request.session:
        messages.error(request, "Session expired. Please register again.")
        return redirect('register')
        
    if request.method == 'POST':
        serializer = OTPVerificationSerializer(data=request.POST)
        if serializer.is_valid():
            reg_data = request.session['registration_data']
            email = reg_data['email']
            otp_code = serializer.validated_data['otp_code']
            
            otp_record = EmailOTP.objects.filter(email=email).first()
            
            if otp_record and otp_record.otp_code == otp_code:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                # OTP is valid! Create the user.
                user = User.objects.create_user(
                    email=email,
                    password=reg_data['password'],
                    display_name=reg_data['display_name'],
                    gender=reg_data['gender']
                )
                
                otp_record.delete()  # Clean up OTP
                del request.session['registration_data'] # Clean up session
                
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, "Account created successfully!")
                return redirect('index')
            else:
                messages.error(request, "Invalid OTP code. Please try again.")
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, error)
                    
    return render(request, 'verify_otp.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = EmailAuthenticationForm(data=request.POST, request=request)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.display_name}!")
            return redirect('index')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = EmailAuthenticationForm(request=request)
    return render(request, 'login.html', {'form': form})

# ----------------------------------------------------
# Custom Forgot Password OTP Views
# ----------------------------------------------------
from .serializers import ForgotPasswordEmailSerializer, ResetPasswordSerializer

def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('index')
        
    if request.method == 'POST':
        serializer = ForgotPasswordEmailSerializer(data=request.POST)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp_code = str(random.randint(100000, 999999))
            
            EmailOTP.objects.update_or_create(email=email, defaults={'otp_code': otp_code})
            
            try:
                send_mail(
                    'Password Reset OTP Code',
                    f'Your password reset verification code is: {otp_code}',
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
                )
            except Exception as e:
                messages.error(request, f"Failed to send email. Error: {str(e)}")
                print(f"EMAIL SEND ERROR: {e}")
                
            request.session['reset_email'] = email
            messages.success(request, f"OTP sent to {email}. Please verify.")
            return redirect('verify_reset_otp')
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, error)
                    
    return render(request, 'forgot_password.html')

def verify_reset_otp_view(request):
    if request.user.is_authenticated:
        return redirect('index')
        
    if 'reset_email' not in request.session:
        messages.error(request, "Session expired. Please request a new OTP.")
        return redirect('forgot_password')
        
    if request.method == 'POST':
        serializer = OTPVerificationSerializer(data=request.POST)
        if serializer.is_valid():
            email = request.session['reset_email']
            otp_code = serializer.validated_data['otp_code']
            
            otp_record = EmailOTP.objects.filter(email=email).first()
            
            if otp_record and otp_record.otp_code == otp_code:
                # Valid OTP! Mark session as authorized to reset password
                request.session['can_reset_password'] = True
                otp_record.delete()
                messages.success(request, "Code verified! Please enter your new password.")
                return redirect('reset_password')
            else:
                messages.error(request, "Invalid OTP code. Please try again.")
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, error)
                    
    return render(request, 'verify_reset_otp.html')

def reset_password_view(request):
    if request.user.is_authenticated:
        return redirect('index')
        
    if not request.session.get('can_reset_password'):
        messages.error(request, "Unauthorized. Please verify your OTP first.")
        return redirect('forgot_password')
        
    if request.method == 'POST':
        serializer = ResetPasswordSerializer(data=request.POST)
        if serializer.is_valid():
            email = request.session.get('reset_email')
            user = get_user_model().objects.get(email=email)
            
            user.set_password(serializer.validated_data['password'])
            user.save()
            
            # Clean up session
            del request.session['reset_email']
            del request.session['can_reset_password']
            
            messages.success(request, "Password has been reset successfully! You can now log in.")
            return redirect('login')
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, error)
                    
    return render(request, 'reset_password.html')

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
    response['Content-Disposition'] = f'attachment; filename="expenses_{request.user.email}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Description', 'Amount', 'Category', 'Date'])
    
    for expense in expenses:
        writer.writerow([expense.description, expense.amount, expense.category, expense.created_at.strftime("%Y-%m-%d")])
        
    return response

@login_required(login_url='login')
def export_excel(request):
    expenses = Expense.objects.filter(user=request.user).order_by('-created_at')
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="expenses_{request.user.email}.xlsx"'
    
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

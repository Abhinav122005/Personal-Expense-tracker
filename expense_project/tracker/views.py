# tracker/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from decimal import Decimal

# Assuming you have defined the Expense model in tracker/models.py
from .models import Expense 

# View to render the main page
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
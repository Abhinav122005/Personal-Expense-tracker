
# Register your models here.
# tracker/admin.py
from django.contrib import admin
from .models import Expense # Import your Expense model

# Option 1: Simple Registration
admin.site.register(Expense)

# OR (Recommended for better layout):

# Option 2: Custom Admin Class
# @admin.register(Expense)
# class ExpenseAdmin(admin.ModelAdmin):
#     list_display = ('description', 'amount', 'category', 'created_at')
#     list_filter = ('category',)
#     search_fields = ('description',)
#     ordering = ('-created_at',)
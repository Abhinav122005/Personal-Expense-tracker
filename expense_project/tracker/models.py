from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserBudget(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username}'s Budget (${self.amount})"

class Expense(models.Model):
    """Represents a single expense transaction."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, 
                                choices=[('Food', 'Food'), 
                                         ('Housing', 'Housing'), 
                                         ('Transport', 'Transport'), 
                                         ('Entertainment', 'Entertainment'), 
                                         ('Other', 'Other')])
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):

        return f"{self.description} (-${self.amount})"

from django.db import models

class Expense(models.Model):
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, 
                                choices=[('Food', 'Food'), 
                                         ('Housing', 'Housing'), 
                                         ('Transport', 'Transport'), 
                                         ('Entertainment', 'Entertainment'), 
                                         ('Other', 'Other')])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):

        return f"{self.description} (-${self.amount})"

from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    username = None  # Remove username field
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=150)
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    
    # Security Question fields
    SECURITY_QUESTIONS = [
        ('pet', 'What was the name of your first pet?'),
        ('city', 'In what city were you born?'),
        ('mother', "What is your mother's maiden name?"),
        ('school', 'What was the name of your first school?'),
        ('car', 'What was the make of your first car?'),
    ]
    security_question = models.CharField(max_length=20, choices=SECURITY_QUESTIONS, blank=True, null=True)
    security_answer = models.CharField(max_length=255, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

class UserBudget(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.email}'s Budget (${self.amount})"

class Expense(models.Model):
    """Represents a single expense transaction."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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

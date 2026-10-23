from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLES = [
        ('admin', 'Admin'),
        ('officer','Procurement Officer'),
        ('manager','manager/Approver'),
        ('vendor','Vendor'),
    ]

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    country = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=ROLES, default='officer')
    info = models.TextField(blank=True)
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']



"""
Registering models in Django Admin
"""
from django.contrib import admin

from .models import GeneralMapping


admin.site.register(GeneralMapping)

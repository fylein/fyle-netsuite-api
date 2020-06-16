"""
Registering models in Django Admin
"""
from django.contrib import admin

from .models import SubsidiaryMapping


admin.site.register(SubsidiaryMapping)

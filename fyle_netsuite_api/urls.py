"""fyle_netsuite_api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('fyle_rest_auth.urls')),
    path('api/workspaces/', include('apps.workspaces.urls')),
    path('api/user/', include('apps.users.urls')),
    path('api/v2/workspaces/', include('apps.workspaces.apis.urls')),
    path('internal_api/', include('apps.internal.urls')),
]

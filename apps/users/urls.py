from django.urls import path

from .views import UserProfileView, FyleOrgsView

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('orgs/', FyleOrgsView.as_view(), name='orgs')
]

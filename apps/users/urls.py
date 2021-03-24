from django.urls import path

from .views import UserProfileView, ClusterDomainView, FyleOrgsView

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('domain/', ClusterDomainView.as_view(), name='domain'),
    path('orgs/', FyleOrgsView.as_view(), name='orgs')
]

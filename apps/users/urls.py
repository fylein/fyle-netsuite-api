from django.urls import path

from .views import UserProfileView, ClusterDomainView

urlpatterns = [
    path('profile/', UserProfileView.as_view()),
    path('domain/', ClusterDomainView.as_view())
]

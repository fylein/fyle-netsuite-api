from django.urls import path

from .views import UserProfileView, ClusterDomainView, FyleOrgsView

urlpatterns = [
    path('profile/', UserProfileView.as_view()),
    path('domain/', ClusterDomainView.as_view()),
    path('orgs/', FyleOrgsView.as_view())
]

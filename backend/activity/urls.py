from django.urls import path

from .views import ActivityDetailView, ActivityListView

urlpatterns = [
    path('', ActivityListView.as_view(), name='activity-list'),
    path('<int:pk>/', ActivityDetailView.as_view(), name='activity-detail'),
]

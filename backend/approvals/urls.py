from django.urls import path

from .views import ApprovalDetailView, ApprovalListView, DecideApprovalView


urlpatterns = [
    path('', ApprovalListView.as_view(), name='approval-list'),
    path('<int:pk>/', ApprovalDetailView.as_view(), name='approval-detail'),
    path('<int:pk>/decide/', DecideApprovalView.as_view(), name='approval-decide'),
]

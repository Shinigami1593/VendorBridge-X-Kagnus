from django.urls import path

from .views import PurchaseOrderDetailView, PurchaseOrderListCreateView


urlpatterns = [
    path('', PurchaseOrderListCreateView.as_view(), name='purchase-order-list'),
    path('<int:pk>/', PurchaseOrderDetailView.as_view(), name='purchase-order-detail'),
]

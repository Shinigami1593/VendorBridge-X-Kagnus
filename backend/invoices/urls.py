from django.urls import path

from .views import (
    InvoiceDetailView,
    InvoiceListCreateView,
    InvoiceMarkPaidView,
    InvoicePdfView,
    InvoiceSendEmailView,
)


urlpatterns = [
    path('', InvoiceListCreateView.as_view(), name='invoice-list'),
    path('<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('<int:pk>/mark-paid/', InvoiceMarkPaidView.as_view(), name='invoice-mark-paid'),
    path('<int:pk>/pdf/', InvoicePdfView.as_view(), name='invoice-pdf'),
    path('<int:pk>/send-email/', InvoiceSendEmailView.as_view(), name='invoice-send-email'),
]

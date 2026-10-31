from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from rfqs.views import MyQuotationsView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/vendors/', include('vendors.urls')),
    path('api/rfqs/', include('rfqs.urls')),
    path('api/my-quotations/', MyQuotationsView.as_view(), name='my-quotations'),
    path('api/dashboard/', include('dashboard.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler500 = 'config.views.server_error'
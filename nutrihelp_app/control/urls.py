from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    # Fases seguintes:
    # path('api/accounts/', include('accounts.urls')),
    # path('api/patients/', include('patients.urls')),
    # path('api/documents/', include('documents.urls')),
    # path('api/chat/', include('chat.urls')),
]

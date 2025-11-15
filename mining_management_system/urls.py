<<<<<<< HEAD
"""
URL configuration for mining_management_system project.
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect, render
from django.conf import settings
from django.conf.urls.static import static
from mining.views import user_logout  # adjust if home_view is elsewhere


# ✅ Simple Home View
def home_view(request):
    return render(request, 'home.html')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Include your main app URLs
    path('mining/', include('mining.urls')),  # added missing trailing slash

    # Django's built-in authentication routes (login, logout, password reset, etc.)
    path('accounts/', include('django.contrib.auth.urls')),
    path('logout/', user_logout, name='logout'),
    # ✅ Home page
    path('home/', home_view, name='home'),
    path('reports/', include('report.urls')), 
    # Redirect root `/` to home or dashboard
    path('', lambda request: redirect('home', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
=======
"""
URL configuration for mining_management_system project.
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect, render
from django.conf import settings
from django.conf.urls.static import static
from mining.views import user_logout  # adjust if home_view is elsewhere


# ✅ Simple Home View
def home_view(request):
    return render(request, 'home.html')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Include your main app URLs
    path('mining/', include('mining.urls')),  # added missing trailing slash

    # Django's built-in authentication routes (login, logout, password reset, etc.)
    path('accounts/', include('django.contrib.auth.urls')),
    path('logout/', user_logout, name='logout'),
    # ✅ Home page
    path('home/', home_view, name='home'),
    path('reports/', include('report.urls')), 
    # Redirect root `/` to home or dashboard
    path('', lambda request: redirect('home', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
>>>>>>> ce25d35ba351259f21575ed2014c56965ea97c25

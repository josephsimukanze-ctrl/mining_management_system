<<<<<<< HEAD
from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_dashboard, name='reports_dashboard'),
    path('production-trend/', views.production_trend, name='production_trend'),
    path('mine-share/', views.mine_share, name='mine_share'),
    path('equipment-status/', views.equipment_status, name='equipment_status'),
    path('workforce/', views.workforce, name='workforce'),
    path('monthly-target/', views.monthly_target, name='monthly_target'),
=======
from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_dashboard, name='reports_dashboard'),
    path('production-trend/', views.production_trend, name='production_trend'),
    path('mine-share/', views.mine_share, name='mine_share'),
    path('equipment-status/', views.equipment_status, name='equipment_status'),
    path('workforce/', views.workforce, name='workforce'),
    path('monthly-target/', views.monthly_target, name='monthly_target'),
>>>>>>> ce25d35ba351259f21575ed2014c56965ea97c25
]
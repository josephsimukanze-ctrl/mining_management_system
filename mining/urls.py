# mining/urls.py
from django.urls import path
from . import views
from .views import user_logout

urlpatterns = [
    # ======================
    # 1. Home & Auth
    # ======================
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('accounts/logout/', user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # ======================
    # 2. Mines
    # ======================
    path('mines/', views.mine_list, name='mine_list'),
    path('mines/create/', views.mine_create, name='mine_create'),
    path('mines/<int:pk>/update/', views.mine_update, name='mine_update'),
    path('mines/<int:pk>/delete/', views.mine_delete, name='mine_delete'),
    path('mines/<int:pk>/', views.mine_detail, name='mine_detail'),
    path('mines/<int:pk>/report/pdf/', views.mine_report_pdf, name='mine_report_pdf'),
    path('mines/<int:pk>/report/annual/', views.annual_report_pdf, name='annual_report_pdf'),

    # ======================
    # 3. Equipment
    # ======================
    path('equipment/', views.equipment_list, name='equipment_list'),
    path('equipment/create/', views.equipment_create, name='equipment_create'),
    path('equipment/<int:pk>/update/', views.equipment_update, name='equipment_update'),
    path('equipment/<int:pk>/delete/', views.equipment_delete, name='equipment_delete'),

    # ======================
    # 4. Employees (FIXED: Removed Duplicate)
    # ======================
    path('employees/', views.employee_dashboard, name='employee_dashboard'),  # ← Main Dashboard
    path('employees/create/', views.employee_create, name='employee_add'),
    path('employees/<int:pk>/update/', views.employee_update, name='employee_update'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('employees/report/pdf/', views.employee_report_pdf, name='employee_report_pdf'),  # ← PDF Export
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),  
    # ======================
    # 5. Production
    # ======================
    path('productions/', views.production_list, name='production_list'),
    path('productions/create/', views.production_create, name='production_create'),
    path('productions/<int:pk>/update/', views.production_update, name='production_update'),
    path('productions/<int:pk>/delete/', views.production_delete, name='production_delete'),
]
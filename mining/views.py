# mining/views.py
import json
import base64
import calendar
from io import BytesIO
from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from .models import Mine, Equipment, Employee, ProductionRecord
from .forms import MineForm, EquipmentForm, EmployeeForm, ProductionRecordForm


# ================================
# AUTH VIEWS
# ================================

def register(request):
    """User registration with success message."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})


def user_login(request):
    """Login with error handling."""
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')


@login_required
def user_logout(request):
    """Logout and redirect to home page."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')


# ================================
# HOME / LANDING PAGE
# ================================

def home(request):
    """
    Public landing page with live, real-time stats for logged-in users.
    Uses Africa/Lusaka (CAT) timezone for all date/time logic.
    Current time: 15 Nov 2025, 10:46 CAT
    """
    now = timezone.now()  # 2025-11-15 10:46 CAT
    today = now.date()    # 2025-11-15

    context = {
        'current_date': today.strftime("%d %B %Y"),  # 15 November 2025
        'current_time': now.strftime("%H:%M"),       # 10:46
        'mines_count': 0,
        'today_production': 0.0,
        'total_employees': 0,
        'total_eq': 0,
        'operational_eq': 0,
        'utilization_rate': 0.0,
        'daily_target': 250,
        'daily_progress': 0.0,
        'is_after_6pm': now.hour >= 18,
    }

    if request.user.is_authenticated:
        user = request.user

        mines_qs = Mine.objects.filter(owner=user)
        equipment_qs = Equipment.objects.filter(owner=user)
        production_today = ProductionRecord.objects.filter(
            owner=user, date=today
        ).aggregate(total=Sum('quantity'))['total'] or 0.0

        mines_count = mines_qs.count()
        total_employees = Employee.objects.filter(owner=user).count()
        total_eq = equipment_qs.count()
        operational_eq = equipment_qs.filter(status='Operational').count()
        utilization = round(operational_eq / total_eq * 100, 1) if total_eq > 0 else 0.0
        daily_progress = round((production_today / 250) * 100, 1)

        context.update({
            'mines_count': mines_count,
            'today_production': production_today,
            'total_employees': total_employees,
            'total_eq': total_eq,
            'operational_eq': operational_eq,
            'utilization_rate': utilization,
            'daily_progress': min(daily_progress, 100),
            'daily_target_met': production_today >= 250,
            'is_after_6pm': now.hour >= 18,
        })

    return render(request, 'home.html', context)


# ================================
# DASHBOARD
# ================================

@login_required
def dashboard(request):
    """Main dashboard with key metrics."""
    user = request.user
    today = date.today()

    mines = Mine.objects.filter(owner=user)
    total_eq = Equipment.objects.filter(mine__owner=user).count()
    operational_eq = Equipment.objects.filter(mine__owner=user, status='Operational').count()
    total_employees = Employee.objects.filter(mine__owner=user).count()

    today_production = ProductionRecord.objects.filter(
        mine__owner=user, date=today
    ).aggregate(total=Sum('quantity'))['total'] or 0

    context = {
        'mines': mines,
        'employees': total_employees,
        'total_eq': total_eq,
        'operational_eq': operational_eq,
        'utilization': round(operational_eq / total_eq * 100, 1) if total_eq else 0,
        'today_production': today_production,
        'daily_target': 250,
        'recent_production': ProductionRecord.objects.filter(mine__owner=user).order_by('-date')[:5],
    }
    return render(request, 'dashboard.html', context)


# ================================
# MINE CRUD
# ================================

@login_required
def mine_list(request):
    mines = Mine.objects.filter(owner=request.user).annotate(
        num_employees=Count('employees', distinct=True),
        num_equipments=Count('equipment', distinct=True)
    )
    active_count = mines.filter(status='Active').count()
    inactive_count = mines.filter(status='Inactive').count()
    total_employees = Employee.objects.filter(mine__owner=request.user).count()

    context = {
        'mines': mines,
        'active_count': active_count,
        'inactive_count': inactive_count,
        'total_employees': total_employees,
    }
    return render(request, 'mine_list.html', context)


@login_required
def mine_detail(request, pk):
    mine = get_object_or_404(Mine, pk=pk, owner=request.user)
    today = date.today()
    start_date = today - timedelta(days=6)

    today_production = ProductionRecord.objects.filter(
        mine=mine, date=today
    ).aggregate(total=Sum('quantity'))['total'] or 0

    records = ProductionRecord.objects.filter(
        mine=mine, date__range=[start_date, today]
    ).values('date').annotate(total=Sum('quantity')).order_by('date')

    dates, values = [], []
    for i in range(7):
        day = start_date + timedelta(days=i)
        record = next((r for r in records if r['date'] == day), None)
        dates.append(day.strftime("%d %b"))
        values.append(record['total'] if record else 0)

    avg_7day = round(sum(values) / 7, 1) if values else 0

    return render(request, 'mine_detail.html', {
        'mine': mine,
        'today_production': today_production,
        'daily_target': 250,
        'production_dates': json.dumps(dates),
        'production_values': json.dumps(values),
        'avg_7day': avg_7day,
    })


@login_required
def mine_create(request):
    if request.method == 'POST':
        form = MineForm(request.POST)
        if form.is_valid():
            mine = form.save(commit=False)
            mine.owner = request.user
            mine.save()
            messages.success(request, f"Mine '{mine.name}' added.")
            return redirect('mine_list')
    else:
        form = MineForm()
    return render(request, 'mine_form.html', {'form': form, 'title': 'Add Mine'})


@login_required
def mine_update(request, pk):
    mine = get_object_or_404(Mine, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = MineForm(request.POST, instance=mine)
        if form.is_valid():
            form.save()
            messages.success(request, f"Mine '{mine.name}' updated.")
            return redirect('mine_list')
    else:
        form = MineForm(instance=mine)
    return render(request, 'mine_form.html', {'form': form, 'title': 'Edit Mine'})


@login_required
def mine_delete(request, pk):
    mine = get_object_or_404(Mine, pk=pk, owner=request.user)
    if request.method == 'POST':
        mine.delete()
        messages.success(request, f"Mine '{mine.name}' deleted.")
        return redirect('mine_list')
    return render(request, 'mine_delete.html', {'mine': mine})


# ================================
# EQUIPMENT CRUD
# ================================

@login_required
def equipment_list(request):
    eqs = Equipment.objects.filter(mine__owner=request.user).select_related('mine')
    total = eqs.count()
    operational = eqs.filter(status='Operational').count()
    maintenance = eqs.filter(status='Maintenance').count()
    utilization = round((operational / total) * 100, 1) if total else 0

    context = {
        'items': eqs,
        'operational_count': operational,
        'maintenance_count': maintenance,
        'utilization': utilization,
    }
    return render(request, 'equipment_list.html', context)


@login_required
def equipment_create(request):
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES)
        if form.is_valid():
            eq = form.save(commit=False)
            eq.owner = request.user
            eq.save()
            messages.success(request, f"Equipment '{eq.name}' added.")
            return redirect('equipment_list')
    else:
        form = EquipmentForm()
    return render(request, 'equipment_form.html', {'form': form, 'title': 'Add Equipment'})


@login_required
def equipment_update(request, pk):
    eq = get_object_or_404(Equipment, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES, instance=eq)
        if form.is_valid():
            form.save()
            messages.success(request, f"Equipment '{eq.name}' updated.")
            return redirect('equipment_list')
    else:
        form = EquipmentForm(instance=eq)
    return render(request, 'equipment_form.html', {'form': form, 'title': 'Edit Equipment'})


@login_required
def equipment_delete(request, pk):
    eq = get_object_or_404(Equipment, pk=pk, owner=request.user)
    if request.method == 'POST':
        eq.delete()
        messages.success(request, "Equipment deleted.")
        return redirect('equipment_list')
    return render(request, 'equipment_delete.html', {'item': eq, 'type': 'Equipment'})


# ================================
# EMPLOYEE CRUD
# ================================

@login_required
def employee_dashboard(request):
    """Main Employee Dashboard with filters and stats."""
    query = request.GET.get('q', '')
    mine_id = request.GET.get('mine', '')

    employees = Employee.objects.filter(owner=request.user)
    if query:
        employees = employees.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(nrc__icontains=query)
        )
    if mine_id:
        employees = employees.filter(mine_id=mine_id)

    stats = {
        'total': employees.count(),
        'active': employees.filter(is_active=True).count(),
        'napsa_compliant': employees.filter(napsa_number__isnull=False).count(),
        'safety_trained': employees.filter(
            last_safety_training__gte=date.today() - timedelta(days=365)
        ).count(),
    }

    mines = Mine.objects.filter(owner=request.user)

    context = {
        'employees': employees,
        'stats': stats,
        'mines': mines,
        'query': query,
        'selected_mine': mine_id,
        'today': date.today().strftime("%d %B %Y"),
        'current_time': timezone.now().strftime("%H:%M"),
    }
    return render(request, 'employee_dashboard.html', context)


@login_required
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.owner = request.user
            emp.save()
            messages.success(request, f"Employee '{emp.get_full_name()}' added.")
            return redirect('employee_dashboard')
    else:
        form = EmployeeForm()
    return render(request, 'employee_form.html', {'form': form, 'title': 'Add Employee'})


@login_required
def employee_update(request, pk):
    emp = get_object_or_404(Employee, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=emp)
        if form.is_valid():
            form.save()
            messages.success(request, f"Employee '{emp.get_full_name()}' updated.")
            return redirect('employee_dashboard')
    else:
        form = EmployeeForm(instance=emp)
    return render(request, 'employee_form.html', {'form': form, 'title': 'Edit Employee'})


@login_required
def employee_delete(request, pk):
    emp = get_object_or_404(Employee, pk=pk, owner=request.user)
    if request.method == 'POST':
        emp.delete()
        messages.success(request, "Employee deleted.")
        return redirect('employee_dashboard')
    return render(request, 'employee_delete.html', {'item': emp, 'type': 'Employee'})

@login_required
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            return redirect('employee_dashboard')
    else:
        form = EmployeeForm(instance=employee)
    return render(request, 'employee_form.html', {'form': form, 'title': 'Edit Employee'})

# ================================
# PRODUCTION CRUD
# ================================

@login_required
def production_list(request):
    records = ProductionRecord.objects.filter(owner=request.user).order_by('-date')
    this_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_total = records.filter(date__gte=this_month).aggregate(total=Sum('quantity'))['total'] or 0
    last_30 = records.filter(date__gte=timezone.now() - timedelta(days=30))
    avg_daily = last_30.aggregate(avg=Avg('quantity'))['avg'] or 0

    return render(request, 'production_list.html', {
        'items': records,
        'monthly_total': monthly_total,
        'avg_daily': round(avg_daily, 1),
    })


@login_required
def production_create(request):
    if request.method == 'POST':
        form = ProductionRecordForm(request.POST)
        if form.is_valid():
            prod = form.save(commit=False)
            prod.owner = request.user
            prod.save()
            messages.success(request, "Production record added.")
            return redirect('production_list')
    else:
        form = ProductionRecordForm()
    return render(request, 'production_form.html', {'form': form, 'title': 'Log Production'})


@login_required
def production_update(request, pk):
    record = get_object_or_404(ProductionRecord, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = ProductionRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Production record updated.")
            return redirect('production_list')
    else:
        form = ProductionRecordForm(instance=record)
    return render(request, 'production_form.html', {'form': form, 'title': 'Edit Production'})


@login_required
def production_delete(request, pk):
    record = get_object_or_404(ProductionRecord, pk=pk, owner=request.user)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "Production record deleted.")
        return redirect('production_list')
    return render(request, 'production_delete.html', {'item': record, 'type': 'Production Record'})


# ================================
# PDF REPORTS
# ================================

def _generate_chart_image(fig):
    buffer = BytesIO()
    canvas = FigureCanvasAgg(fig)
    canvas.print_png(buffer)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode()


@login_required
def mine_report_pdf(request, pk):
    mine = get_object_or_404(Mine, pk=pk, owner=request.user)
    today = date.today()
    start_date = today - timedelta(days=29)

    records = ProductionRecord.objects.filter(
        mine=mine, date__range=[start_date, today]
    ).order_by('-date')

    total = records.aggregate(total=Sum('quantity'))['total'] or 0
    avg_daily = round(total / 30, 1)

    chart_image = None
    if total > 0:
        daily_data = records.values('date').annotate(daily=Sum('quantity')).order_by('date')
        dates = [entry['date'].strftime("%d %b") for entry in daily_data]
        values = [entry['daily'] for entry in daily_data]

        fig = Figure(figsize=(8, 4))
        ax = fig.add_subplot(111)
        ax.plot(dates, values, marker='o', color='#16A34A', linewidth=2)
        ax.fill_between(dates, values, alpha=0.1, color='#16A34A')
        ax.set_title(f'30-Day Production - {mine.name}')
        ax.set_ylabel('Tons')
        ax.grid(True, alpha=0.3)
        chart_image = _generate_chart_image(fig)

    context = {
        'mine': mine,
        'generated_date': today.strftime("%d %B %Y"),
        'generated_time': timezone.now().strftime("%H:%M CAT"),
        'monthly_total': total,
        'avg_daily': avg_daily,
        'daily_target': 250,
        'chart_image': chart_image,
        'recent_logs': records[:10],
    }

    html_string = render_to_string('pdf/mine_report.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"ZM_MineReport_{mine.name.replace(' ', '_')}_{today}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def annual_report_pdf(request, pk):
    mine = get_object_or_404(Mine, pk=pk, owner=request.user)
    year = date.today().year
    monthly_data = []
    total_production = 0
    target_monthly = 2500

    for month in range(1, 13):
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        total = ProductionRecord.objects.filter(
            mine=mine, date__range=[start, end]
        ).aggregate(t=Sum('quantity'))['t'] or 0

        percent = round(total / target_monthly * 100, 1) if target_monthly else 0
        monthly_data.append({
            'month': calendar.month_abbr[month],
            'total': total,
            'target': target_monthly,
            'percent': percent,
        })
        total_production += total

    avg_monthly = round(total_production / 12, 1)

    chart_image = None
    if total_production > 0:
        months = [m['month'] for m in monthly_data]
        values = [m['total'] for m in monthly_data]
        targets = [m['target'] for m in monthly_data]

        fig = Figure(figsize=(10, 5))
        ax = fig.add_subplot(111)
        x = range(len(months))
        ax.bar(x, values, color='#16A34A', alpha=0.8, label='Actual')
        ax.plot(x, targets, color='#DC2626', linestyle='--', marker='o', label='Target')
        ax.set_xticks(x)
        ax.set_xticklabels(months)
        ax.set_title(f'{year} Production - {mine.name}')
        ax.set_ylabel('Tons')
        ax.legend()
        ax.grid(True, alpha=0.3)
        chart_image = _generate_chart_image(fig)

    context = {
        'mine': mine,
        'year': year,
        'generated_date': date.today().strftime("%d %B %Y"),
        'generated_time': timezone.now().strftime("%H:%M CAT"),
        'total_production': total_production,
        'avg_monthly': avg_monthly,
        'monthly_data': monthly_data,
        'monthly_chart': chart_image,
        'total_employees': Employee.objects.filter(mine=mine).count(),
    }

    html_string = render_to_string('pdf/annual_report.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"ZM_AnnualReport_{year}_{mine.name.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ================================
# EMPLOYEE PDF REPORT
# ================================

@login_required
def employee_report_pdf(request):
    employees = Employee.objects.filter(owner=request.user).select_related('mine')
    total = employees.count()
    napsa_compliant = employees.filter(napsa_number__isnull=False).count()

    context = {
        'employees': employees,
        'total': total,
        'napsa_compliant': napsa_compliant,
        'generated_date': date.today().strftime("%d %B %Y"),
        'generated_time': timezone.now().strftime("%H:%M CAT"),
    }

    html_string = render_to_string('pdf/employee_report.html', context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"ZM_EmployeeReport_{date.today()}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
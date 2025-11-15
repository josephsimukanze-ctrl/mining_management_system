<<<<<<< HEAD
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta, date
from django.db.models import Sum, Count
from mining.models import Mine, ProductionRecord, Equipment, Employee
from .models import Report
import json

@login_required
def reports_dashboard(request):
    context = {
        'reports': [
            {'name': 'Production Trend', 'url': 'production_trend', 'icon': '📈'},
            {'name': 'Mine Output Share', 'url': 'mine_share', 'icon': '🥧'},
            {'name': 'Equipment Status', 'url': 'equipment_status', 'icon': '📊'},
            {'name': 'Workforce by Mine', 'url': 'workforce', 'icon': '👥'},
            {'name': 'Monthly Target vs Actual', 'url': 'monthly_target', 'icon': '🎯'},
        ]
    }
    return render(request, 'report/dashboard.html', context)

@login_required
def production_trend(request):
    end_date = date.today()
    start_date = end_date - timedelta(days=29)
    records = ProductionRecord.objects.filter(
        owner=request.user, date__range=[start_date, end_date]
    ).values('date').annotate(total=Sum('quantity')).order_by('date')

    dates = []
    values = []
    for i in range(30):
        day = start_date + timedelta(days=i)
        rec = next((r for r in records if r['date'] == day), None)
        dates.append(day.strftime("%d %b"))
        values.append(round(rec['total'], 1) if rec else 0)

    chart_data = {
        'labels': dates,
        'datasets': [{
            'label': 'Daily Output (tons)',
            'data': values,
            'borderColor': '#10b981',
            'backgroundColor': 'rgba(16, 185, 129, 0.1)',
            'tension': 0.4,
            'fill': True
        }]
    }

    return render(request, 'report/chart.html', {
        'title': '30-Day Production Trend',
        'chart_type': 'line',
        'chart_data': json.dumps(chart_data),
        'summary': f"Total: {sum(values):.1f} t | Avg: {sum(values)/30:.1f} t/day"
    })

@login_required
def mine_share(request):
    mines = Mine.objects.filter(owner=request.user)
    data = []
    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
    
    for i, mine in enumerate(mines):
        total = ProductionRecord.objects.filter(mine=mine).aggregate(t=Sum('quantity'))['t'] or 0
        data.append({
            'label': mine.name,
            'value': round(total, 1),
            'color': colors[i % len(colors)]
        })

    chart_data = {
        'labels': [d['label'] for d in data],
        'datasets': [{
            'data': [d['value'] for d in data],
            'backgroundColor': [d['color'] for d in data]
        }]
    }

    return render(request, 'report/chart.html', {
        'title': 'Mine Output Share',
        'chart_type': 'pie',
        'chart_data': json.dumps(chart_data),
        'summary': f"{len(mines)} mines • Total: {sum(d['value'] for d in data):.1f} t"
    })
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count, F
from mining.models import Equipment, Mine

@login_required
def equipment_status(request):
    """
    Equipment Status Report: calculates hours to service, availability, and counts.
    """

    # Get all equipment for mines owned by the user
    user_equipment = Equipment.objects.filter(mine__owner=request.user).select_related('mine')

    # Prepare equipment data with safe calculations
    equipment_data = []
    for eq in user_equipment:
        # Ensure last_service_hours and hours_used are numbers
        last_service = eq.last_service_hours or 0
        hours_used = eq.hours_used or 0
        hours_to_service = max(0, 250 - (hours_used - last_service))  # prevent negative

        equipment_data.append({
            'instance': eq,
            'mine_name': eq.mine.name,
            'hours_to_service': hours_to_service
        })

    # Summary statistics
    total_equipment = user_equipment.count()
    operational_count = user_equipment.filter(status='Operational').count()
    maintenance_count = user_equipment.filter(status='Maintenance').count()
    down_count = total_equipment - operational_count
    availability_percent = round((operational_count / total_equipment) * 100, 1) if total_equipment else 0

    context = {
        'title': 'Equipment Status Report',
        'equipment_data': sorted(equipment_data, key=lambda x: x['hours_to_service']),  # sort by urgency
        'total_equipment': total_equipment,
        'operational_count': operational_count,
        'maintenance_count': maintenance_count,
        'down_count': down_count,
        'availability_percent': availability_percent,
    }

    return render(request, 'report/equipment_status.html', context)



from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count
import json
from mining.models import Mine

@login_required
def workforce(request):
    """
    Workforce report per mine for the logged-in user.
    """
    # Corrected annotation using the related_name 'employees'
    mines = Mine.objects.filter(owner=request.user).annotate(
        emp_count=Count('employees', distinct=True)
    )

    # Prepare chart data
    chart_data = {
        'labels': [m.name for m in mines],
        'datasets': [{
            'label': 'Employees',
            'data': [m.emp_count for m in mines],
            'backgroundColor': '#8b5cf6'
        }]
    }

    return render(request, 'report/chart.html', {
        'title': 'Workforce by Mine',
        'chart_type': 'bar',
        'chart_data': json.dumps(chart_data),
        'summary': f"{sum(m.emp_count for m in mines)} total employees"
    })

@login_required
def monthly_target(request):
    year = 2025
    monthly = []
    actuals = []
    targets = [2500] * 12  # 100 t/day * 25 days

    for month in range(1, 13):
        start = date(year, month, 1)
        end = date(year, month, 28) if month != 2 else date(year, 2, 28)
        total = ProductionRecord.objects.filter(
            owner=request.user, date__range=[start, end]
        ).aggregate(t=Sum('quantity'))['t'] or 0
        monthly.append(total)
        actuals.append(targets[month-1])

    chart_data = {
        'labels': ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
        'datasets': [
            {
                'label': 'Actual',
                'data': monthly,
                'type': 'bar',
                'backgroundColor': '#10b981'
            },
            {
                'label': 'Target',
                'data': actuals,
                'type': 'line',
                'borderColor': '#dc2626',
                'backgroundColor': 'transparent',
                'borderDash': [5, 5]
            }
        ]
    }

    return render(request, 'report/chart.html', {
        'title': '2025 Monthly Target vs Actual',
        'chart_type': 'bar',  # Combo handled in JS
        'chart_data': json.dumps(chart_data),
        'summary': f"Target: 30,000 t/year | Achieved: {sum(monthly):.1f} t"
})
import json
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from mining.models import ProductionRecord

@login_required
def production_trend(request):
    # Aggregate production by mine
    mines = ProductionRecord.objects.filter(mine__owner=request.user).values('mine__name').annotate(
        total_qty=Sum('quantity')
    )

    chart_data = {
        'labels': [m['mine__name'] for m in mines],
        'datasets': [{
            'label': 'Production Quantity',
            'data': [float(m['total_qty'] or 0) for m in mines],  # ✅ convert Decimal to float
            'backgroundColor': '#4ade80'
        }]
    }

    return render(request, 'report/chart.html', {
        'title': 'Production Trend',
        'chart_type': 'line',
        'chart_data': json.dumps(chart_data),
        'summary': f"{sum(float(m['total_qty'] or 0) for m in mines)} total units"
    })
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum, F
import json

@login_required
def mine_share(request):
    # Get mines for this user
    mines = Mine.objects.filter(owner=request.user)

    # Calculate total production for each mine
    data_labels = []
    data_values = []

    for mine in mines:
        total_prod = mine.production_records.aggregate(total=Sum('quantity'))['total'] or 0
        data_labels.append(mine.name)
        data_values.append(float(total_prod))  # ✅ convert Decimal to float

    chart_data = {
        'labels': data_labels,
        'datasets': [{
            'label': 'Production Share',
            'data': data_values,
            'backgroundColor': ['#6366f1', '#ec4899', '#facc15', '#10b981', '#f97316'][:len(data_labels)]
        }]
    }

    return render(request, 'report/chart.html', {
        'title': 'Mine Production Share',
        'chart_type': 'doughnut',
        'chart_data': json.dumps(chart_data),
        'summary': f"{sum(data_values)} total units produced"
    })
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum
import json

@login_required
def monthly_target(request):
    # Example: get monthly production totals per mine
    mines = Mine.objects.filter(owner=request.user)
    
    labels = []
    target_values = []
    actual_values = []

    for mine in mines:
        labels.append(mine.name)
        # Convert Decimals to float for JSON serialization
        target = float(mine.production_records.aggregate(total_target=Sum('monthly_target'))['total_target'] or 0)
        actual = float(mine.production_records.aggregate(total_actual=Sum('quantity'))['total_actual'] or 0)
        target_values.append(target)
        actual_values.append(actual)

    chart_data = {
        'labels': labels,
        'datasets': [
            {
                'label': 'Target',
                'data': target_values,
                'backgroundColor': '#3b82f6'
            },
            {
                'label': 'Actual',
                'data': actual_values,
                'backgroundColor': '#10b981'
            }
        ]
    }

    return render(request, 'report/chart.html', {
        'title': 'Monthly Production vs Target',
        'chart_type': 'bar',
        'chart_data': json.dumps(chart_data),
        'summary': f"Total target: {sum(target_values)}, Total actual: {sum(actual_values)}"
    })
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum
import json

@login_required
def monthly_target(request):
    mines = Mine.objects.filter(owner=request.user)

    labels = []
    target_values = []
    actual_values = []

    for mine in mines:
        labels.append(mine.name)
        # Example fixed target (replace with actual value if needed)
        target = 1000
        actual = float(mine.production_records.aggregate(total_actual=Sum('quantity'))['total_actual'] or 0)
        target_values.append(target)
        actual_values.append(actual)

    chart_data = {
        'labels': labels,
        'datasets': [
            {
                'label': 'Target',
                'data': target_values,
                'backgroundColor': '#3b82f6'
            },
            {
                'label': 'Actual',
                'data': actual_values,
                'backgroundColor': '#10b981'
            }
        ]
    }

    return render(request, 'report/chart.html', {
        'title': 'Monthly Production vs Target',
        'chart_type': 'bar',
        'chart_data': json.dumps(chart_data),
        'summary': f"Total target: {sum(target_values)}, Total actual: {sum(actual_values)}"
    })
=======
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta, date
from django.db.models import Sum, Count
from mining.models import Mine, ProductionRecord, Equipment, Employee
from .models import Report
import json

@login_required
def reports_dashboard(request):
    context = {
        'reports': [
            {'name': 'Production Trend', 'url': 'production_trend', 'icon': '📈'},
            {'name': 'Mine Output Share', 'url': 'mine_share', 'icon': '🥧'},
            {'name': 'Equipment Status', 'url': 'equipment_status', 'icon': '📊'},
            {'name': 'Workforce by Mine', 'url': 'workforce', 'icon': '👥'},
            {'name': 'Monthly Target vs Actual', 'url': 'monthly_target', 'icon': '🎯'},
        ]
    }
    return render(request, 'report/dashboard.html', context)

@login_required
def production_trend(request):
    end_date = date.today()
    start_date = end_date - timedelta(days=29)
    records = ProductionRecord.objects.filter(
        owner=request.user, date__range=[start_date, end_date]
    ).values('date').annotate(total=Sum('quantity')).order_by('date')

    dates = []
    values = []
    for i in range(30):
        day = start_date + timedelta(days=i)
        rec = next((r for r in records if r['date'] == day), None)
        dates.append(day.strftime("%d %b"))
        values.append(round(rec['total'], 1) if rec else 0)

    chart_data = {
        'labels': dates,
        'datasets': [{
            'label': 'Daily Output (tons)',
            'data': values,
            'borderColor': '#10b981',
            'backgroundColor': 'rgba(16, 185, 129, 0.1)',
            'tension': 0.4,
            'fill': True
        }]
    }

    return render(request, 'report/chart.html', {
        'title': '30-Day Production Trend',
        'chart_type': 'line',
        'chart_data': json.dumps(chart_data),
        'summary': f"Total: {sum(values):.1f} t | Avg: {sum(values)/30:.1f} t/day"
    })

@login_required
def mine_share(request):
    mines = Mine.objects.filter(owner=request.user)
    data = []
    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
    
    for i, mine in enumerate(mines):
        total = ProductionRecord.objects.filter(mine=mine).aggregate(t=Sum('quantity'))['t'] or 0
        data.append({
            'label': mine.name,
            'value': round(total, 1),
            'color': colors[i % len(colors)]
        })

    chart_data = {
        'labels': [d['label'] for d in data],
        'datasets': [{
            'data': [d['value'] for d in data],
            'backgroundColor': [d['color'] for d in data]
        }]
    }

    return render(request, 'report/chart.html', {
        'title': 'Mine Output Share',
        'chart_type': 'pie',
        'chart_data': json.dumps(chart_data),
        'summary': f"{len(mines)} mines • Total: {sum(d['value'] for d in data):.1f} t"
    })
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count, F
from mining.models import Equipment, Mine

@login_required
def equipment_status(request):
    """
    Equipment Status Report: calculates hours to service, availability, and counts.
    """

    # Get all equipment for mines owned by the user
    user_equipment = Equipment.objects.filter(mine__owner=request.user).select_related('mine')

    # Prepare equipment data with safe calculations
    equipment_data = []
    for eq in user_equipment:
        # Ensure last_service_hours and hours_used are numbers
        last_service = eq.last_service_hours or 0
        hours_used = eq.hours_used or 0
        hours_to_service = max(0, 250 - (hours_used - last_service))  # prevent negative

        equipment_data.append({
            'instance': eq,
            'mine_name': eq.mine.name,
            'hours_to_service': hours_to_service
        })

    # Summary statistics
    total_equipment = user_equipment.count()
    operational_count = user_equipment.filter(status='Operational').count()
    maintenance_count = user_equipment.filter(status='Maintenance').count()
    down_count = total_equipment - operational_count
    availability_percent = round((operational_count / total_equipment) * 100, 1) if total_equipment else 0

    context = {
        'title': 'Equipment Status Report',
        'equipment_data': sorted(equipment_data, key=lambda x: x['hours_to_service']),  # sort by urgency
        'total_equipment': total_equipment,
        'operational_count': operational_count,
        'maintenance_count': maintenance_count,
        'down_count': down_count,
        'availability_percent': availability_percent,
    }

    return render(request, 'report/equipment_status.html', context)



from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count
import json
from mining.models import Mine

@login_required
def workforce(request):
    """
    Workforce report per mine for the logged-in user.
    """
    # Corrected annotation using the related_name 'employees'
    mines = Mine.objects.filter(owner=request.user).annotate(
        emp_count=Count('employees', distinct=True)
    )

    # Prepare chart data
    chart_data = {
        'labels': [m.name for m in mines],
        'datasets': [{
            'label': 'Employees',
            'data': [m.emp_count for m in mines],
            'backgroundColor': '#8b5cf6'
        }]
    }

    return render(request, 'report/chart.html', {
        'title': 'Workforce by Mine',
        'chart_type': 'bar',
        'chart_data': json.dumps(chart_data),
        'summary': f"{sum(m.emp_count for m in mines)} total employees"
    })

@login_required
def monthly_target(request):
    year = 2025
    monthly = []
    actuals = []
    targets = [2500] * 12  # 100 t/day * 25 days

    for month in range(1, 13):
        start = date(year, month, 1)
        end = date(year, month, 28) if month != 2 else date(year, 2, 28)
        total = ProductionRecord.objects.filter(
            owner=request.user, date__range=[start, end]
        ).aggregate(t=Sum('quantity'))['t'] or 0
        monthly.append(total)
        actuals.append(targets[month-1])

    chart_data = {
        'labels': ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
        'datasets': [
            {
                'label': 'Actual',
                'data': monthly,
                'type': 'bar',
                'backgroundColor': '#10b981'
            },
            {
                'label': 'Target',
                'data': actuals,
                'type': 'line',
                'borderColor': '#dc2626',
                'backgroundColor': 'transparent',
                'borderDash': [5, 5]
            }
        ]
    }

    return render(request, 'report/chart.html', {
        'title': '2025 Monthly Target vs Actual',
        'chart_type': 'bar',  # Combo handled in JS
        'chart_data': json.dumps(chart_data),
        'summary': f"Target: 30,000 t/year | Achieved: {sum(monthly):.1f} t"
})
import json
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from mining.models import ProductionRecord

@login_required
def production_trend(request):
    # Aggregate production by mine
    mines = ProductionRecord.objects.filter(mine__owner=request.user).values('mine__name').annotate(
        total_qty=Sum('quantity')
    )

    chart_data = {
        'labels': [m['mine__name'] for m in mines],
        'datasets': [{
            'label': 'Production Quantity',
            'data': [float(m['total_qty'] or 0) for m in mines],  # ✅ convert Decimal to float
            'backgroundColor': '#4ade80'
        }]
    }

    return render(request, 'report/chart.html', {
        'title': 'Production Trend',
        'chart_type': 'line',
        'chart_data': json.dumps(chart_data),
        'summary': f"{sum(float(m['total_qty'] or 0) for m in mines)} total units"
    })
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum, F
import json

@login_required
def mine_share(request):
    # Get mines for this user
    mines = Mine.objects.filter(owner=request.user)

    # Calculate total production for each mine
    data_labels = []
    data_values = []

    for mine in mines:
        total_prod = mine.production_records.aggregate(total=Sum('quantity'))['total'] or 0
        data_labels.append(mine.name)
        data_values.append(float(total_prod))  # ✅ convert Decimal to float

    chart_data = {
        'labels': data_labels,
        'datasets': [{
            'label': 'Production Share',
            'data': data_values,
            'backgroundColor': ['#6366f1', '#ec4899', '#facc15', '#10b981', '#f97316'][:len(data_labels)]
        }]
    }

    return render(request, 'report/chart.html', {
        'title': 'Mine Production Share',
        'chart_type': 'doughnut',
        'chart_data': json.dumps(chart_data),
        'summary': f"{sum(data_values)} total units produced"
    })
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum
import json

@login_required
def monthly_target(request):
    # Example: get monthly production totals per mine
    mines = Mine.objects.filter(owner=request.user)
    
    labels = []
    target_values = []
    actual_values = []

    for mine in mines:
        labels.append(mine.name)
        # Convert Decimals to float for JSON serialization
        target = float(mine.production_records.aggregate(total_target=Sum('monthly_target'))['total_target'] or 0)
        actual = float(mine.production_records.aggregate(total_actual=Sum('quantity'))['total_actual'] or 0)
        target_values.append(target)
        actual_values.append(actual)

    chart_data = {
        'labels': labels,
        'datasets': [
            {
                'label': 'Target',
                'data': target_values,
                'backgroundColor': '#3b82f6'
            },
            {
                'label': 'Actual',
                'data': actual_values,
                'backgroundColor': '#10b981'
            }
        ]
    }

    return render(request, 'report/chart.html', {
        'title': 'Monthly Production vs Target',
        'chart_type': 'bar',
        'chart_data': json.dumps(chart_data),
        'summary': f"Total target: {sum(target_values)}, Total actual: {sum(actual_values)}"
    })
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum
import json

@login_required
def monthly_target(request):
    mines = Mine.objects.filter(owner=request.user)

    labels = []
    target_values = []
    actual_values = []

    for mine in mines:
        labels.append(mine.name)
        # Example fixed target (replace with actual value if needed)
        target = 1000
        actual = float(mine.production_records.aggregate(total_actual=Sum('quantity'))['total_actual'] or 0)
        target_values.append(target)
        actual_values.append(actual)

    chart_data = {
        'labels': labels,
        'datasets': [
            {
                'label': 'Target',
                'data': target_values,
                'backgroundColor': '#3b82f6'
            },
            {
                'label': 'Actual',
                'data': actual_values,
                'backgroundColor': '#10b981'
            }
        ]
    }

    return render(request, 'report/chart.html', {
        'title': 'Monthly Production vs Target',
        'chart_type': 'bar',
        'chart_data': json.dumps(chart_data),
        'summary': f"Total target: {sum(target_values)}, Total actual: {sum(actual_values)}"
    })
>>>>>>> ce25d35ba351259f21575ed2014c56965ea97c25

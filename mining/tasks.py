from celery import shared_task
from django.utils import timezone
from datetime import datetime, time
from .models import Employee, ProductionRecord, Equipment
from .sms import send_sms

@shared_task
def send_shift_start_alert():
    now = timezone.localtime()
    if now.time() < time(7, 5) and now.time() >= time(7, 0):
        employees = Employee.objects.filter(receive_sms=True, phone__startswith='+260')
        for emp in employees:
            msg = f"ZM MINING: Good morning {emp.first_name}! Shift starts at 07:00. Report to {emp.mine.name}."
            send_sms(emp.phone, msg)

@shared_task
def send_shift_end_alert():
    now = timezone.localtime()
    if now.time() < time(19, 5) and now.time() >= time(19, 0):
        employees = Employee.objects.filter(receive_sms=True, phone__startswith='+260')
        for emp in employees:
            msg = f"ZM MINING: Shift ending at 19:00. Safe journey home from {emp.mine.name}!"
            send_sms(emp.phone, msg)

@shared_task
def check_daily_production():
    today = timezone.now().date()
    records = ProductionRecord.objects.filter(date=today)
    total = records.aggregate(t=Sum('quantity'))['t'] or 0

    if total < 200:
        managers = Employee.objects.filter(role='Manager', receive_sms=True)
        for mgr in managers:
            msg = f"ALERT: Low production today! Only {total} tons logged. Target: 250 t."
            send_sms(mgr.phone, msg)

@shared_task
def check_equipment_service():
    due = Equipment.objects.filter(
        hours_used__gte=F('last_service_hours') + 250
    )
    for eq in due:
        msg = f"SERVICE DUE: {eq.type} at {eq.mine.name} has {eq.hours_used} hrs. Schedule maintenance!"
        # Send to manager
        mgr = Employee.objects.filter(mine=eq.mine, receive_sms=True).first()
        if mgr:
            send_sms(mgr.phone, msg)
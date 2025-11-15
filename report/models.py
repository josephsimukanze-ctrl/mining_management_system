<<<<<<< HEAD
from django.db import models
from django.contrib.auth.models import User
from mining.models import Mine, ProductionRecord, Equipment, Employee

class Report(models.Model):
    REPORT_TYPES = [
        ('production_trend', 'Production Trend (Line)'),
        ('mine_share', 'Mine Output Share (Pie)'),
        ('equipment_status', 'Equipment Status (Bar)'),
        ('workforce', 'Workforce by Mine (Bar)'),
        ('monthly_target', 'Monthly Target vs Actual (Combo)'),
    ]
    title = models.CharField(max_length=100, choices=REPORT_TYPES)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.JSONField(default=dict)  # Store chart data

    def _str_(self):
=======
from django.db import models
from django.contrib.auth.models import User
from mining.models import Mine, ProductionRecord, Equipment, Employee

class Report(models.Model):
    REPORT_TYPES = [
        ('production_trend', 'Production Trend (Line)'),
        ('mine_share', 'Mine Output Share (Pie)'),
        ('equipment_status', 'Equipment Status (Bar)'),
        ('workforce', 'Workforce by Mine (Bar)'),
        ('monthly_target', 'Monthly Target vs Actual (Combo)'),
    ]
    title = models.CharField(max_length=100, choices=REPORT_TYPES)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.JSONField(default=dict)  # Store chart data

    def _str_(self):
>>>>>>> ce25d35ba351259f21575ed2014c56965ea97c25
        return f"{self.get_title_display()} - {self.generated_at.strftime('%d %b %Y')}"
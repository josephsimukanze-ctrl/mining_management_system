<<<<<<< HEAD
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal

# ===== ROLES =====
class Role(models.Model):
    """Employee roles (e.g., Operator, Mechanic, Supervisor)"""
    name = models.CharField(max_length=50, unique=True, help_text="e.g., Excavator Operator")

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ['name']

    def __str__(self):
        return self.name


# ===== MINES =====
class Mine(models.Model):
    """Zambian mine with ZEMA license & GPS"""
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., Kitwe, Copperbelt")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mines')

    # GPS Coordinates (Zambia range)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        default=Decimal('-13.000000'),
        validators=[MinValueValidator(Decimal('-18.0')), MaxValueValidator(Decimal('-8.0'))],
        help_text="Latitude: -8.0 to -18.0 (Zambia)"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        default=Decimal('28.000000'),
        validators=[MinValueValidator(Decimal('22.0')), MaxValueValidator(Decimal('34.0'))],
        help_text="Longitude: 22.0 to 34.0 (Zambia)"
    )

    license_doc = models.FileField(
        upload_to='mines/licenses/',
        blank=True, null=True,
        help_text="Upload ZEMA or Ministry of Mines license (PDF/Image)"
    )
    license_expiry = models.DateField(null=True, blank=True, help_text="License expiry date")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mine"
        verbose_name_plural = "Mines"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def employee_count(self):
        return self.employees.count()

    @property
    def equipment_count(self):
        return self.equipment.count()

    @property
    def is_license_expired(self):
        if not self.license_expiry:
            return False
        return self.license_expiry < timezone.now().date()

    @property
    def days_until_expiry(self):
        if not self.license_expiry:
            return None
        delta = self.license_expiry - timezone.now().date()
        return max(delta.days, 0)

# ===== EQUIPMENT =====
class Equipment(models.Model):
    """ZABS-compliant equipment with 250-hour service cycle"""
    STATUS_CHOICES = [
        ('Operational', 'Operational'),
        ('Maintenance', 'Maintenance'),
        ('Down', 'Down'),
    ]

    TYPE_CHOICES = [
        ('EX', 'Excavator'),
        ('HL', 'Haul Truck'),
        ('DR', 'Drill Rig'),
        ('LD', 'Loader'),
        ('BL', 'Bulldozer'),
        ('GR', 'Grader'),
        ('CR', 'Crane'),
        ('OT', 'Other'),
    ]

    serial_number = models.CharField(max_length=50, unique=True, help_text="e.g., EX-001")
    type = models.CharField(max_length=2, choices=TYPE_CHOICES, default='OT')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='Operational')
    mine = models.ForeignKey(Mine, on_delete=models.CASCADE, related_name='equipment')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='equipment')
    last_service = models.DateField(null=True, blank=True)
    last_service_hours = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    hours_used = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    fuel_type = models.CharField(max_length=20, default="Diesel")
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Equipment"
        verbose_name_plural = "Equipment"
        ordering = ['mine', 'serial_number']
        unique_together = ['mine', 'serial_number']

    def __str__(self):
        return f"{self.serial_number} - {self.get_type_display()} ({self.mine.name})"

    @property
    def hours_to_service(self):
        remaining = Decimal('250.0') - (self.hours_used - self.last_service_hours)
        return max(remaining, Decimal('0.0'))

    @property
    def is_service_due(self):
        return self.hours_to_service <= Decimal('25.0')

    @property
    def is_overdue(self):
        return self.hours_used - self.last_service_hours > Decimal('250.0')

    @property
    def service_status(self):
        if self.is_overdue:
            return "OVERDUE"
        elif self.is_service_due:
            return "DUE SOON"
        else:
            return "ON TRACK"


# ===== EMPLOYEES =====
# mining/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError
from datetime import timedelta


# ================================
# EMPLOYEE – ZM MINING ROLES
# ================================
class Employee(models.Model):
    """
    ZEMA, NAPSA, and Ministry of Mines compliant employee.
    Current time: 15 Nov 2025, 10:55 AM CAT
    """

    # === ZM MINING ROLES (Industry Standard) ===
    ROLES = [
        # Management
        ('General Manager', 'General Manager'),
        ('Mine Manager', 'Mine Manager'),
        ('Operations Manager', 'Operations Manager'),
        ('HR Manager', 'HR Manager'),
        
        # Supervisors
        ('Shift Supervisor', 'Shift Supervisor'),
        ('Section Supervisor', 'Section Supervisor'),
        ('Safety Supervisor', 'Safety Supervisor'),
        
        # Operators
        ('Drill Operator', 'Drill Operator'),
        ('Blasting Operator', 'Blasting Operator'),
        ('Loader Operator', 'Loader Operator'),
        ('Haul Truck Driver', 'Haul Truck Driver'),
        ('Excavator Operator', 'Excavator Operator'),
        
        # Technicians
        ('Mechanical Technician', 'Mechanical Technician'),
        ('Electrical Technician', 'Electrical Technician'),
        ('Instrumentation Technician', 'Instrumentation Technician'),
        ('Auto Electrician', 'Auto Electrician'),
        
        # Safety & Environment
        ('Safety Officer', 'Safety Officer'),
        ('Environmental Officer', 'Environmental Officer'),
        ('First Aider', 'First Aider'),
        
        # Support
        ('Storeman', 'Storeman'),
        ('Security Officer', 'Security Officer'),
        ('Cleaner', 'Cleaner'),
        ('Cook', 'Cook'),
    ]

    # === Core Identity ===
    first_name = models.CharField(max_length=100, help_text="e.g., John")
    last_name = models.CharField(max_length=100, help_text="e.g., Mwansa")
    
    # === Compliance ===
    nrc = models.CharField(
        max_length=15,
        unique=True,
        validators=[RegexValidator(
            regex=r'^\d{6}/\d{2}/\d{1}$',
            message="NRC: 123456/78/9"
        )],
        help_text="National Registration Card"
    )
    napsa_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        help_text="NAPSA Registration Number"
    )

    # === Assignment ===
    role = models.CharField(
        max_length=50,
        choices=ROLES,
        help_text="ZM mining job role"
    )
    mine = models.ForeignKey(
        'Mine', on_delete=models.CASCADE,
        related_name='employees',
        help_text="Assigned mine"
    )
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='employees',
        help_text="System user"
    )

    # === Contact ===
    phone = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\+260\d{9}$',
            message="+260971234567"
        )],
        help_text="SMS alerts"
    )
    receive_sms = models.BooleanField(default=True, help_text="Shift & safety alerts")

    # === Employment ===
    date_joined = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    last_safety_training = models.DateField(
        null=True, blank=True,
        help_text="ZEMA annual training"
    )

    # === Media ===
    photo = models.ImageField(
        upload_to='employees/photos/',
        blank=True, null=True,
        help_text="ID photo"
    )

    # === Audit ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # === Meta ===
    class Meta:
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
        ordering = ['mine__name', 'last_name', 'first_name']
        unique_together = ['mine', 'nrc']
        permissions = [
            ("can_export_napsa", "Can export NAPSA report"),
            ("can_view_safety", "Can view training records"),
            ("can_manage_shifts", "Can assign shifts"),
        ]

    # === Methods ===
    def __str__(self):
        return f"{self.get_full_name()} - {self.role} ({self.mine.name})"

    def get_full_name(self):
        return f"{self.first_name.strip().title()} {self.last_name.strip().title()}"

    def get_absolute_url(self):
        return reverse('employee_detail', kwargs={'pk': self.pk})

    @property
    def is_napsa_compliant(self):
        return bool(self.napsa_number)

    @property
    def needs_safety_training(self):
        if not self.last_safety_training:
            return True
        due = self.last_safety_training + timedelta(days=365)
        return due <= timezone.now().date() + timedelta(days=30)

    @property
    def role_category(self):
        """Group roles for filtering."""
        if self.role in ['General Manager', 'Mine Manager', 'Operations Manager', 'HR Manager']:
            return "Management"
        elif 'Supervisor' in self.role:
            return "Supervisors"
        elif 'Operator' in self.role or 'Driver' in self.role:
            return "Operators"
        elif 'Technician' in self.role or 'Electrician' in self.role:
            return "Technicians"
        elif 'Safety' in self.role or 'Environmental' in self.role or 'First Aider' in self.role:
            return "Safety & Environment"
        else:
            return "Support"

    def clean(self):
        if self.napsa_number and len(self.napsa_number) < 6:
            raise ValidationError("NAPSA number too short.")
        if self.phone and not self.phone.startswith('+260'):
            raise ValidationError("Phone must start with +260")

    def save(self, *args, **kwargs):
        self.first_name = self.first_name.title()
        self.last_name = self.last_name.title()
        super().save(*args, **kwargs)

# ===== PRODUCTION RECORDS =====
class ProductionRecord(models.Model):
    date = models.DateField(default=timezone.now)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))]
    )
    mine = models.ForeignKey(Mine, on_delete=models.CASCADE, related_name='production_records')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='production_records')
    notes = models.TextField(blank=True)
    logged_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Production Record"
        verbose_name_plural = "Production Records"
        ordering = ['-date', '-logged_at']
        unique_together = ['mine', 'date']

    def __str__(self):
        return f"{self.mine.name}: {self.quantity} tons on {self.date.strftime('%d %b %Y')}"

    @property
    def is_late(self):
        if self.date != self.logged_at.date():
            return True
        return self.logged_at.time() > timezone.datetime.strptime("18:00", "%H:%M").time()

    @property
    def daily_target_met(self):
        return self.quantity >= Decimal('250.00')
# mining/models.py
from django.db import models

class Equipment(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    quantity = models.IntegerField()
    mine = models.ForeignKey(Mine, on_delete=models.CASCADE, related_name='equipment')
    type = models.CharField(max_length=50)
    last_service = models.DateField()
    status = models.CharField(max_length=50)

    def __str__(self):
        return self.name
=======
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal

# ===== ROLES =====
class Role(models.Model):
    """Employee roles (e.g., Operator, Mechanic, Supervisor)"""
    name = models.CharField(max_length=50, unique=True, help_text="e.g., Excavator Operator")

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ['name']

    def __str__(self):
        return self.name


# ===== MINES =====
class Mine(models.Model):
    """Zambian mine with ZEMA license & GPS"""
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., Kitwe, Copperbelt")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mines')

    # GPS Coordinates (Zambia range)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        default=Decimal('-13.000000'),
        validators=[MinValueValidator(Decimal('-18.0')), MaxValueValidator(Decimal('-8.0'))],
        help_text="Latitude: -8.0 to -18.0 (Zambia)"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        default=Decimal('28.000000'),
        validators=[MinValueValidator(Decimal('22.0')), MaxValueValidator(Decimal('34.0'))],
        help_text="Longitude: 22.0 to 34.0 (Zambia)"
    )

    license_doc = models.FileField(
        upload_to='mines/licenses/',
        blank=True, null=True,
        help_text="Upload ZEMA or Ministry of Mines license (PDF/Image)"
    )
    license_expiry = models.DateField(null=True, blank=True, help_text="License expiry date")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mine"
        verbose_name_plural = "Mines"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def employee_count(self):
        return self.employees.count()

    @property
    def equipment_count(self):
        return self.equipment.count()

    @property
    def is_license_expired(self):
        if not self.license_expiry:
            return False
        return self.license_expiry < timezone.now().date()

    @property
    def days_until_expiry(self):
        if not self.license_expiry:
            return None
        delta = self.license_expiry - timezone.now().date()
        return max(delta.days, 0)

# ===== EQUIPMENT =====
class Equipment(models.Model):
    """ZABS-compliant equipment with 250-hour service cycle"""
    STATUS_CHOICES = [
        ('Operational', 'Operational'),
        ('Maintenance', 'Maintenance'),
        ('Down', 'Down'),
    ]

    TYPE_CHOICES = [
        ('EX', 'Excavator'),
        ('HL', 'Haul Truck'),
        ('DR', 'Drill Rig'),
        ('LD', 'Loader'),
        ('BL', 'Bulldozer'),
        ('GR', 'Grader'),
        ('CR', 'Crane'),
        ('OT', 'Other'),
    ]

    serial_number = models.CharField(max_length=50, unique=True, help_text="e.g., EX-001")
    type = models.CharField(max_length=2, choices=TYPE_CHOICES, default='OT')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='Operational')
    mine = models.ForeignKey(Mine, on_delete=models.CASCADE, related_name='equipment')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='equipment')
    last_service = models.DateField(null=True, blank=True)
    last_service_hours = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    hours_used = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    fuel_type = models.CharField(max_length=20, default="Diesel")
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Equipment"
        verbose_name_plural = "Equipment"
        ordering = ['mine', 'serial_number']
        unique_together = ['mine', 'serial_number']

    def __str__(self):
        return f"{self.serial_number} - {self.get_type_display()} ({self.mine.name})"

    @property
    def hours_to_service(self):
        remaining = Decimal('250.0') - (self.hours_used - self.last_service_hours)
        return max(remaining, Decimal('0.0'))

    @property
    def is_service_due(self):
        return self.hours_to_service <= Decimal('25.0')

    @property
    def is_overdue(self):
        return self.hours_used - self.last_service_hours > Decimal('250.0')

    @property
    def service_status(self):
        if self.is_overdue:
            return "OVERDUE"
        elif self.is_service_due:
            return "DUE SOON"
        else:
            return "ON TRACK"


# ===== EMPLOYEES =====
# mining/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError
from datetime import timedelta


# ================================
# EMPLOYEE – ZM MINING ROLES
# ================================
class Employee(models.Model):
    """
    ZEMA, NAPSA, and Ministry of Mines compliant employee.
    Current time: 15 Nov 2025, 10:55 AM CAT
    """

    # === ZM MINING ROLES (Industry Standard) ===
    ROLES = [
        # Management
        ('General Manager', 'General Manager'),
        ('Mine Manager', 'Mine Manager'),
        ('Operations Manager', 'Operations Manager'),
        ('HR Manager', 'HR Manager'),
        
        # Supervisors
        ('Shift Supervisor', 'Shift Supervisor'),
        ('Section Supervisor', 'Section Supervisor'),
        ('Safety Supervisor', 'Safety Supervisor'),
        
        # Operators
        ('Drill Operator', 'Drill Operator'),
        ('Blasting Operator', 'Blasting Operator'),
        ('Loader Operator', 'Loader Operator'),
        ('Haul Truck Driver', 'Haul Truck Driver'),
        ('Excavator Operator', 'Excavator Operator'),
        
        # Technicians
        ('Mechanical Technician', 'Mechanical Technician'),
        ('Electrical Technician', 'Electrical Technician'),
        ('Instrumentation Technician', 'Instrumentation Technician'),
        ('Auto Electrician', 'Auto Electrician'),
        
        # Safety & Environment
        ('Safety Officer', 'Safety Officer'),
        ('Environmental Officer', 'Environmental Officer'),
        ('First Aider', 'First Aider'),
        
        # Support
        ('Storeman', 'Storeman'),
        ('Security Officer', 'Security Officer'),
        ('Cleaner', 'Cleaner'),
        ('Cook', 'Cook'),
    ]

    # === Core Identity ===
    first_name = models.CharField(max_length=100, help_text="e.g., John")
    last_name = models.CharField(max_length=100, help_text="e.g., Mwansa")
    
    # === Compliance ===
    nrc = models.CharField(
        max_length=15,
        unique=True,
        validators=[RegexValidator(
            regex=r'^\d{6}/\d{2}/\d{1}$',
            message="NRC: 123456/78/9"
        )],
        help_text="National Registration Card"
    )
    napsa_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        help_text="NAPSA Registration Number"
    )

    # === Assignment ===
    role = models.CharField(
        max_length=50,
        choices=ROLES,
        help_text="ZM mining job role"
    )
    mine = models.ForeignKey(
        'Mine', on_delete=models.CASCADE,
        related_name='employees',
        help_text="Assigned mine"
    )
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='employees',
        help_text="System user"
    )

    # === Contact ===
    phone = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\+260\d{9}$',
            message="+260971234567"
        )],
        help_text="SMS alerts"
    )
    receive_sms = models.BooleanField(default=True, help_text="Shift & safety alerts")

    # === Employment ===
    date_joined = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    last_safety_training = models.DateField(
        null=True, blank=True,
        help_text="ZEMA annual training"
    )

    # === Media ===
    photo = models.ImageField(
        upload_to='employees/photos/',
        blank=True, null=True,
        help_text="ID photo"
    )

    # === Audit ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # === Meta ===
    class Meta:
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
        ordering = ['mine__name', 'last_name', 'first_name']
        unique_together = ['mine', 'nrc']
        permissions = [
            ("can_export_napsa", "Can export NAPSA report"),
            ("can_view_safety", "Can view training records"),
            ("can_manage_shifts", "Can assign shifts"),
        ]

    # === Methods ===
    def __str__(self):
        return f"{self.get_full_name()} - {self.role} ({self.mine.name})"

    def get_full_name(self):
        return f"{self.first_name.strip().title()} {self.last_name.strip().title()}"

    def get_absolute_url(self):
        return reverse('employee_detail', kwargs={'pk': self.pk})

    @property
    def is_napsa_compliant(self):
        return bool(self.napsa_number)

    @property
    def needs_safety_training(self):
        if not self.last_safety_training:
            return True
        due = self.last_safety_training + timedelta(days=365)
        return due <= timezone.now().date() + timedelta(days=30)

    @property
    def role_category(self):
        """Group roles for filtering."""
        if self.role in ['General Manager', 'Mine Manager', 'Operations Manager', 'HR Manager']:
            return "Management"
        elif 'Supervisor' in self.role:
            return "Supervisors"
        elif 'Operator' in self.role or 'Driver' in self.role:
            return "Operators"
        elif 'Technician' in self.role or 'Electrician' in self.role:
            return "Technicians"
        elif 'Safety' in self.role or 'Environmental' in self.role or 'First Aider' in self.role:
            return "Safety & Environment"
        else:
            return "Support"

    def clean(self):
        if self.napsa_number and len(self.napsa_number) < 6:
            raise ValidationError("NAPSA number too short.")
        if self.phone and not self.phone.startswith('+260'):
            raise ValidationError("Phone must start with +260")

    def save(self, *args, **kwargs):
        self.first_name = self.first_name.title()
        self.last_name = self.last_name.title()
        super().save(*args, **kwargs)

# ===== PRODUCTION RECORDS =====
class ProductionRecord(models.Model):
    date = models.DateField(default=timezone.now)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))]
    )
    mine = models.ForeignKey(Mine, on_delete=models.CASCADE, related_name='production_records')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='production_records')
    notes = models.TextField(blank=True)
    logged_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Production Record"
        verbose_name_plural = "Production Records"
        ordering = ['-date', '-logged_at']
        unique_together = ['mine', 'date']

    def __str__(self):
        return f"{self.mine.name}: {self.quantity} tons on {self.date.strftime('%d %b %Y')}"

    @property
    def is_late(self):
        if self.date != self.logged_at.date():
            return True
        return self.logged_at.time() > timezone.datetime.strptime("18:00", "%H:%M").time()

    @property
    def daily_target_met(self):
        return self.quantity >= Decimal('250.00')
# mining/models.py
from django.db import models

class Equipment(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    quantity = models.IntegerField()
    mine = models.ForeignKey(Mine, on_delete=models.CASCADE, related_name='equipment')
    type = models.CharField(max_length=50)
    last_service = models.DateField()
    status = models.CharField(max_length=50)

    def __str__(self):
        return self.name
>>>>>>> ce25d35ba351259f21575ed2014c56965ea97c25

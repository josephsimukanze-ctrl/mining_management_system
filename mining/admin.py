from django.contrib import admin
from .models import Mine, Equipment, Employee, ProductionRecord, Role


@admin.register(Mine)
class MineAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'status', 'owner')
    search_fields = ('name', 'location')
    list_filter = ('status',)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('type', 'mine', 'status', 'last_service')
    search_fields = ('type',)
    list_filter = ('status', 'mine')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


# mining/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import Employee, Mine


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """
    ZM Mining Employee Admin – Ministry of Mines, NAPSA, ZEMA Ready
    Current time: 15 Nov 2025, 10:58 AM CAT
    """
    # === List View ===
    list_display = (
        'photo_thumb',
        'full_name',
        'nrc',
        'role_badge',
        'mine_link',
        'phone',
        'napsa_status',
        'safety_status',
        'is_active',
        'owner',
        'date_joined',
    )
    list_display_links = ('full_name', 'nrc')
    list_per_page = 25
    ordering = ('mine__name', 'last_name', 'first_name')

    # === Search ===
    search_fields = (
        'first_name__icontains',
        'last_name__icontains',
        'nrc',
        'napsa_number',
        'phone',
        'mine__name',
    )
    search_help_text = "Search by name, NRC, NAPSA, phone, or mine"

    # === Filters ===
    list_filter = (
        'mine',
        'role',
        'is_active',
        'receive_sms',
        ('last_safety_training', admin.DateFieldListFilter),
        ('date_joined', admin.DateFieldListFilter),
        'owner',
    )

    # === Fieldsets (Edit Form) ===
    fieldsets = (
        ("Identity", {
            'fields': ('first_name', 'last_name', 'nrc', 'napsa_number')
        }),
        ("Assignment", {
            'fields': ('role', 'mine', 'owner')
        }),
        ("Contact", {
            'fields': ('phone', 'receive_sms')
        }),
        ("Employment", {
            'fields': ('date_joined', 'is_active', 'last_safety_training')
        }),
        ("Media", {
            'fields': ('photo',),
            'description': "Upload clear ID photo for security & audit"
        }),
    )

    # === Readonly (Audit) ===
    readonly_fields = ('created_at', 'updated_at')

    # === Custom Columns ===
    def photo_thumb(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" class="w-10 h-10 rounded-full object-cover border-2 border-gray-300" />',
                obj.photo.url
            )
        return format_html(
            '<div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center text-white font-bold text-xs">'
            '{}</div>',
            obj.first_name[0].upper() + obj.last_name[0].upper()
        )
    photo_thumb.short_description = "Photo"

    def full_name(self, obj):
        return obj.get_full_name()
    full_name.short_description = "Name"
    full_name.admin_order_field = 'last_name'

    def role_badge(self, obj):
        colors = {
            'Management': 'bg-blue-100 text-blue-800',
            'Supervisors': 'bg-purple-100 text-purple-800',
            'Operators': 'bg-green-100 text-green-800',
            'Technicians': 'bg-yellow-100 text-yellow-800',
            'Safety & Environment': 'bg-red-100 text-red-800',
            'Support': 'bg-gray-100 text-gray-800',
        }
        category = obj.role_category
        color = colors.get(category, 'bg-gray-100 text-gray-800')
        return format_html(
            '<span class="inline-block px-3 py-1 text-xs font-bold rounded-full {}">{}</span>',
            color, obj.role
        )
    role_badge.short_description = "Role"

    def mine_link(self, obj):
        url = reverse('admin:mining_mine_change', args=[obj.mine.pk])
        return format_html('<a href="{}" class="text-blue-600 hover:underline font-medium">{}</a>', url, obj.mine.name)
    mine_link.short_description = "Mine"
    mine_link.admin_order_field = 'mine__name'

    def napsa_status(self, obj):
        if obj.is_napsa_compliant:
            return format_html('<span class="text-green-600 text-xl">Checkmark</span>')
        return format_html('<span class="text-red-600 text-xl">Cross</span>')
    napsa_status.short_description = "NAPSA"
    napsa_status.boolean = True

    def safety_status(self, obj):
        if not obj.last_safety_training:
            return format_html('<span class="text-red-600 text-xs font-bold">NO TRAINING</span>')
        days = obj.days_since_training
        if days > 365:
            return format_html('<span class="text-red-600 text-xs font-bold">EXPIRED</span>')
        elif days > 335:
            return format_html('<span class="text-orange-600 text-xs font-bold">DUE SOON</span>')
        else:
            return format_html('<span class="text-green-600 text-xs font-bold">VALID</span>')
    safety_status.short_description = "Safety Training"

    # === Actions ===
    actions = ['mark_active', 'mark_inactive', 'export_napsa_csv']

    def mark_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} employees marked active.")
    mark_active.short_description = "Mark selected as Active"

    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} employees marked inactive.")
    mark_inactive.short_description = "Mark selected as Inactive"

    def export_napsa_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="NAPSA_Employees.csv"'
        writer = csv.writer(response)
        writer.writerow(['NRC', 'Name', 'NAPSA Number', 'Mine', 'Role', 'Phone'])
        for emp in queryset.filter(napsa_number__isnull=False):
            writer.writerow([emp.nrc, emp.get_full_name(), emp.napsa_number, emp.mine.name, emp.role, emp.phone])
        return response
    export_napsa_csv.short_description = "Export selected to NAPSA CSV"

    # === Permissions ===
    def has_export_napsa_permission(self, request):
        return request.user.has_perm('mining.can_export_napsa')

    # === Inlines (Optional) ===
    # inlines = [ShiftInline, TrainingInline]

@admin.register(ProductionRecord)
class ProductionRecordAdmin(admin.ModelAdmin):
    list_display = ('mine', 'quantity', 'date', 'owner')
    list_filter = ('mine', 'date')
    search_fields = ('mine__name',)
    date_hierarchy = 'date'

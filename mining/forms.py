from django import forms
from .models import Mine, Equipment, Employee, ProductionRecord
from django.utils import timezone


class MineForm(forms.ModelForm):
    class Meta:
        model = Mine
        fields = ['name', 'location', 'status','license_doc','latitude','longitude']


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['type', 'status', 'mine','last_service']
        widget={
            'last_service':forms.DateInput(attrs={'type':'date'})
        }

from django import forms
from .models import Employee
# mining/forms.py
from django import forms
from django.core.validators import RegexValidator
from .models import Employee, Mine

class EmployeeForm(forms.ModelForm):
    """
    ZM Mining Employee Form – NAPSA, ZEMA, NRC, SMS, Safety Training
    Current time: 15 Nov 2025, 10:56 AM CAT
    """

    # === NRC: ZM Format 123456/78/9 ===
    nrc = forms.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\d{6}/\d{2}/\d{1}$',
                message="NRC format: 123456/78/9"
            )
        ],
        widget=forms.TextInput(attrs={
            'placeholder': '123456/78/9',
            'pattern': r'\d{6}/\d{2}/\d{1}',
            'title': 'NRC: 6 digits / 2 digits / 1 digit',
            'class': 'border border-gray-300 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition',
        }),
        help_text="National Registration Card (NRC)"
    )

    # === NAPSA Number ===
    napsa_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., NAPSA123456',
            'class': 'border border-gray-300 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-green-500 focus:border-green-500 transition',
        }),
        help_text="NAPSA Registration Number (Required for payroll)"
    )

    # === Role: 22 ZM Mining Roles (from model) ===
    role = forms.ChoiceField(
        choices=Employee.ROLES,
        widget=forms.Select(attrs={
            'class': 'border border-gray-300 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition',
        }),
        help_text="Select job role"
    )

    # === Phone: +260 format ===
    phone = forms.CharField(
        max_length=15,
        required=False,
        validators=[
            RegexValidator(
                regex=r'^\+260\d{9}$',
                message="Format: +260971234567"
            )
        ],
        widget=forms.TextInput(attrs={
            'placeholder': '+260971234567',
            'class': 'border border-gray-300 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition',
        }),
        help_text="Mobile for SMS alerts"
    )

    # === Safety Training Date ===
    last_safety_training = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'border border-gray-300 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition',
            }
        ),
        help_text="Last ZEMA safety training (required annually)"
    )

    class Meta:
        model = Employee
        fields = [
            'first_name', 'last_name', 'nrc', 'napsa_number',
            'role', 'mine', 'phone', 'receive_sms',
            'date_joined', 'is_active', 'last_safety_training', 'photo'
        ]
        widgets = {
            # === Names ===
            'first_name': forms.TextInput(attrs={
                'placeholder': 'e.g., John',
                'class': 'border border-gray-300 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition',
            }),
            'last_name': forms.TextInput(attrs={
                'placeholder': 'e.g., Mwansa',
                'class': 'border border-gray-300 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition',
            }),

            # === Mine ===
            'mine': forms.Select(attrs={
                'class': 'border border-gray-300 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition',
            }),

            # === Booleans ===
            'receive_sms': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-green-600 border-gray-300 rounded focus:ring-green-500',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500',
            }),

            # === Dates ===
            'date_joined': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'border border-gray-300 rounded-lg px-4 py-2 w-full focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition',
                }
            ),

            # === Photo ===
            'photo': forms.ClearableFileInput(attrs={
                'id': 'photo-input',
                'class': 'hidden',
                'accept': 'image/*',
            }),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'nrc': 'NRC',
            'napsa_number': 'NAPSA Number',
            'role': 'Role',
            'mine': 'Assigned Mine',
            'phone': 'Phone',
            'receive_sms': 'Receive SMS Alerts',
            'date_joined': 'Date Joined',
            'is_active': 'Active Employee',
            'last_safety_training': 'Last Safety Training',
            'photo': 'Photo',
        }
        help_texts = {
            'receive_sms': 'Get shift, safety, and payday alerts via SMS',
            'is_active': 'Uncheck if employee has left',
            'photo': 'Upload clear ID photo for security & audit',
        }

    # === Limit Mine Choices to User ===
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['mine'].queryset = Mine.objects.filter(owner=user).order_by('name')
        # Set initial date_joined to today
        if not self.instance.pk:
            self.fields['date_joined'].initial = timezone.now().date()
class ProductionRecordForm(forms.ModelForm):
    class Meta:
        model = ProductionRecord
        fields = ['date', 'quantity', 'mine']

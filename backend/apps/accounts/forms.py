from django import forms
from django.contrib.auth import authenticate
from django.db import transaction

from .models import LandlordProfile, StudentProfile, User


class WebLoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Mat khau", widget=forms.PasswordInput)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        if email and password:
            self.user = authenticate(self.request, email=email, password=password)
            if self.user is None:
                raise forms.ValidationError("Email hoac mat khau khong dung.")
            if not self.user.is_active:
                raise forms.ValidationError("Tai khoan da bi vo hieu hoa.")
        return cleaned_data


class WebRegisterForm(forms.Form):
    ROLE_CHOICES = (
        (User.Role.STUDENT, "Sinh vien"),
        (User.Role.LANDLORD, "Chu tro"),
    )

    full_name = forms.CharField(label="Ho ten", max_length=255)
    email = forms.EmailField(label="Email")
    phone = forms.CharField(label="So dien thoai", max_length=20, required=False)
    role = forms.ChoiceField(label="Vai tro", choices=ROLE_CHOICES)
    password1 = forms.CharField(label="Mat khau", min_length=8, widget=forms.PasswordInput)
    password2 = forms.CharField(label="Nhap lai mat khau", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email nay da duoc su dung.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            raise forms.ValidationError("Hai mat khau khong khop.")
        return cleaned_data

    @transaction.atomic
    def save(self):
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
            full_name=self.cleaned_data["full_name"],
            phone=self.cleaned_data["phone"],
            role=self.cleaned_data["role"],
        )
        if user.role == User.Role.STUDENT:
            StudentProfile.objects.create(user=user)
        else:
            LandlordProfile.objects.create(user=user)
        return user


class WebProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("full_name", "phone")
        labels = {
            "full_name": "Ho ten",
            "phone": "So dien thoai",
        }


class StudentPreferenceForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ("university", "student_code", "budget_min", "budget_max", "max_distance_km")
        labels = {
            "university": "Truong dai hoc",
            "student_code": "Ma sinh vien",
            "budget_min": "Ngan sach tu",
            "budget_max": "Ngan sach den",
            "max_distance_km": "Khoang cach toi da",
        }


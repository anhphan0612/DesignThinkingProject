from django import forms
from django.contrib.auth import authenticate
from django.db import transaction

from .models import LandlordProfile, StudentProfile, User


class WebLoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Mật khẩu", widget=forms.PasswordInput)

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
                raise forms.ValidationError("Email hoặc mật khẩu không đúng.")
            if not self.user.is_active:
                raise forms.ValidationError("Tài khoản đã bị vô hiệu hóa.")
        return cleaned_data


class WebRegisterForm(forms.Form):
    ROLE_CHOICES = (
        (User.Role.STUDENT, "Sinh viên"),
        (User.Role.LANDLORD, "Chủ trọ"),
    )

    full_name = forms.CharField(label="Họ tên", max_length=255)
    email = forms.EmailField(label="Email")
    phone = forms.CharField(label="Số điện thoại", max_length=20, required=False)
    role = forms.ChoiceField(label="Vai trò", choices=ROLE_CHOICES)
    password1 = forms.CharField(label="Mật khẩu", min_length=8, widget=forms.PasswordInput)
    password2 = forms.CharField(label="Nhập lại mật khẩu", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email này đã được sử dụng.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            raise forms.ValidationError("Hai mật khẩu không khớp.")
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
            "full_name": "Họ tên",
            "phone": "Số điện thoại",
        }


class StudentPreferenceForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ("university", "student_code", "budget_min", "budget_max", "max_distance_km")
        labels = {
            "university": "Trường đại học",
            "student_code": "Mã sinh viên",
            "budget_min": "Ngân sách từ",
            "budget_max": "Ngân sách đến",
            "max_distance_km": "Khoảng cách tối đa",
        }


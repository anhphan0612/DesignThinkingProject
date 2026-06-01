from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from allauth.socialaccount.models import SocialApp
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .forms import StudentPreferenceForm, WebLoginForm, WebProfileForm, WebRegisterForm
from .serializers import (
    LandlordProfileSerializer,
    LoginSerializer,
    RegisterSerializer,
    StudentProfileSerializer,
    UserSerializer,
)


class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.STUDENT


class RegisterAPIView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(
            {
                "token": serializer.validated_data["token"].key,
                "user": UserSerializer(serializer.validated_data["user"]).data,
            }
        )


class MeAPIView(APIView):
    def get(self, request):
        data = UserSerializer(request.user, context={"request": request}).data
        if request.user.role == User.Role.STUDENT:
            data["profile"] = StudentProfileSerializer(request.user.student_profile).data
        elif request.user.role == User.Role.LANDLORD:
            data["profile"] = LandlordProfileSerializer(request.user.landlord_profile).data
        return Response(data)

    def patch(self, request):
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class StudentPreferenceAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsStudent]
    serializer_class = StudentProfileSerializer

    def get_object(self):
        return self.request.user.student_profile


def configured_social_providers():
    return set(SocialApp.objects.values_list("provider", flat=True))


def web_login(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = WebLoginForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        messages.success(request, "Đăng nhập thành công.")
        return redirect(request.GET.get("next") or "home")
    return render(
        request,
        "accounts/login.html",
        {"form": form, "social_providers": configured_social_providers()},
    )


def web_register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = WebRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Tạo tài khoản thành công.")
        return redirect("home")
    return render(
        request,
        "accounts/register.html",
        {"form": form, "social_providers": configured_social_providers()},
    )


@login_required
def web_logout(request):
    logout(request)
    messages.success(request, "Đã đăng xuất.")
    return redirect("home")


@login_required
def web_profile(request):
    profile_form = WebProfileForm(request.POST or None, instance=request.user)
    preference_form = None
    if request.user.role == User.Role.STUDENT and hasattr(request.user, "student_profile"):
        preference_form = StudentPreferenceForm(request.POST or None, instance=request.user.student_profile)

    if request.method == "POST":
        forms = [profile_form]
        if preference_form is not None:
            forms.append(preference_form)
        if all(form.is_valid() for form in forms):
            profile_form.save()
            if preference_form is not None:
                preference_form.save()
            messages.success(request, "Đã cập nhật hồ sơ.")
            return redirect("web-profile")

    return render(
        request,
        "accounts/profile.html",
        {"profile_form": profile_form, "preference_form": preference_form},
    )

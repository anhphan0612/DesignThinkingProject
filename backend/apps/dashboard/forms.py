from django import forms
from django.contrib.gis.geos import Point

from apps.listings.models import Amenity, Room, RoomImage


class RoomForm(forms.ModelForm):
    latitude = forms.DecimalField(label="Vi do", max_digits=9, decimal_places=6)
    longitude = forms.DecimalField(label="Kinh do", max_digits=9, decimal_places=6)
    amenities = forms.ModelMultipleChoiceField(
        label="Tien ich",
        queryset=Amenity.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Room
        fields = (
            "ward",
            "title",
            "description",
            "address",
            "latitude",
            "longitude",
            "price",
            "deposit",
            "area",
            "max_occupants",
            "gender_policy",
            "electricity_price",
            "water_price",
            "amenities",
        )
        labels = {
            "ward": "Phuong",
            "title": "Tieu de",
            "description": "Mo ta",
            "address": "Dia chi",
            "price": "Gia thue",
            "deposit": "Tien coc",
            "area": "Dien tich",
            "max_occupants": "So nguoi toi da",
            "gender_policy": "Gioi tinh",
            "electricity_price": "Gia dien",
            "water_price": "Gia nuoc",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["latitude"].initial = self.instance.location.y
            self.fields["longitude"].initial = self.instance.location.x

    def save(self, commit=True):
        room = super().save(commit=False)
        room.location = Point(
            float(self.cleaned_data["longitude"]),
            float(self.cleaned_data["latitude"]),
            srid=4326,
        )
        if commit:
            room.save()
            self.save_m2m()
        return room


class LandlordRoomImageForm(forms.ModelForm):
    class Meta:
        model = RoomImage
        fields = ("image", "caption", "is_cover", "sort_order")
        labels = {
            "image": "Anh",
            "caption": "Chu thich",
            "is_cover": "Dat lam anh bia",
            "sort_order": "Thu tu hien thi",
        }


class RejectRoomForm(forms.Form):
    reason = forms.CharField(label="Ly do tu choi", widget=forms.Textarea)


class RejectImageForm(forms.Form):
    moderation_note = forms.CharField(label="Ly do tu choi", widget=forms.Textarea)


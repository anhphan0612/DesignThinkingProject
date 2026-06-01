from django import forms
from django.contrib.gis.geos import Point

from apps.listings.models import Amenity, Room, RoomImage


class RoomForm(forms.ModelForm):
    latitude = forms.DecimalField(label="Vĩ độ", max_digits=9, decimal_places=6)
    longitude = forms.DecimalField(label="Kinh độ", max_digits=9, decimal_places=6)
    amenities = forms.ModelMultipleChoiceField(
        label="Tiện ích",
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
            "ward": "Phường",
            "title": "Tiêu đề",
            "description": "Mô tả",
            "address": "Địa chỉ",
            "price": "Giá thuê",
            "deposit": "Tiền cọc",
            "area": "Diện tích",
            "max_occupants": "Số người tối đa",
            "gender_policy": "Giới tính",
            "electricity_price": "Giá điện",
            "water_price": "Giá nước",
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
            "image": "Ảnh",
            "caption": "Chú thích",
            "is_cover": "Đặt làm ảnh bìa",
            "sort_order": "Thứ tự hiển thị",
        }


class RejectRoomForm(forms.Form):
    reason = forms.CharField(label="Lý do từ chối", widget=forms.Textarea)


class RejectImageForm(forms.Form):
    moderation_note = forms.CharField(label="Lý do từ chối", widget=forms.Textarea)


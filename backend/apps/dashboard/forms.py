from django import forms
from django.contrib.gis.geos import Point

from apps.listings.models import Amenity, Room, RoomImage
from apps.listings.validators import validate_room_image_upload


DEFAULT_ROOM_POINT = {
    "latitude": "21.028511",
    "longitude": "105.804817",
}


class RoomForm(forms.ModelForm):
    latitude = forms.DecimalField(
        label="Vĩ độ bản đồ",
        max_digits=9,
        decimal_places=6,
        required=False,
        widget=forms.HiddenInput,
    )
    longitude = forms.DecimalField(
        label="Kinh độ bản đồ",
        max_digits=9,
        decimal_places=6,
        required=False,
        widget=forms.HiddenInput,
    )
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
            "price": "Giá thuê (VND/tháng)",
            "deposit": "Tiền cọc (VND)",
            "area": "Diện tích (m²)",
            "max_occupants": "Số người tối đa",
            "gender_policy": "Giới tính phù hợp",
            "electricity_price": "Giá điện (VND/kWh)",
            "water_price": "Giá nước (VND/m³)",
        }
        help_texts = {
            "address": "Nhập số nhà/ngõ, tên đường và khu vực. Khi lưu, hệ thống sẽ thử ghim vị trí theo phường/quận đã chọn.",
            "price": "Ví dụ: 2500000 cho 2.500.000 VND/tháng.",
            "deposit": "Có thể bỏ trống nếu không yêu cầu cọc.",
            "electricity_price": "Có thể bỏ trống nếu đã bao gồm trong giá thuê.",
            "water_price": "Có thể bỏ trống nếu đã bao gồm trong giá thuê.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        numeric_rules = {
            "price": {"min": "1", "step": "1", "inputmode": "numeric", "placeholder": "2500000"},
            "deposit": {"min": "0", "step": "1", "inputmode": "numeric", "placeholder": "2500000"},
            "area": {"min": "1", "step": "0.1", "placeholder": "24"},
            "max_occupants": {"min": "1", "step": "1", "placeholder": "2"},
            "electricity_price": {"min": "0", "step": "1", "inputmode": "numeric", "placeholder": "4000"},
            "water_price": {"min": "0", "step": "1", "inputmode": "numeric", "placeholder": "20000"},
        }
        for field_name, attrs in numeric_rules.items():
            self.fields[field_name].widget.attrs.update(attrs)
        if self.instance and self.instance.pk:
            self.fields["latitude"].initial = self.instance.location.y
            self.fields["longitude"].initial = self.instance.location.x
        else:
            self.fields["latitude"].initial = DEFAULT_ROOM_POINT["latitude"]
            self.fields["longitude"].initial = DEFAULT_ROOM_POINT["longitude"]

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get("price")
        deposit = cleaned_data.get("deposit")
        area = cleaned_data.get("area")
        max_occupants = cleaned_data.get("max_occupants")
        electricity_price = cleaned_data.get("electricity_price")
        water_price = cleaned_data.get("water_price")
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")

        if price is not None and price <= 0:
            self.add_error("price", "Giá thuê phải lớn hơn 0 VND.")
        if deposit is not None and deposit < 0:
            self.add_error("deposit", "Tiền cọc không được âm.")
        if price is not None and deposit is not None and deposit > price * 6:
            self.add_error("deposit", "Tiền cọc đang quá cao so với giá thuê. Hãy kiểm tra lại.")
        if area is not None and area <= 0:
            self.add_error("area", "Diện tích phải lớn hơn 0 m².")
        if max_occupants is not None and max_occupants <= 0:
            self.add_error("max_occupants", "Số người tối đa phải lớn hơn 0.")
        if electricity_price is not None and electricity_price < 0:
            self.add_error("electricity_price", "Giá điện không được âm.")
        if water_price is not None and water_price < 0:
            self.add_error("water_price", "Giá nước không được âm.")
        if latitude is not None and not -90 <= latitude <= 90:
            self.add_error("latitude", "Vĩ độ không hợp lệ.")
        if longitude is not None and not -180 <= longitude <= 180:
            self.add_error("longitude", "Kinh độ không hợp lệ.")
        return cleaned_data

    def save(self, commit=True):
        room = super().save(commit=False)
        latitude = self.cleaned_data.get("latitude") or DEFAULT_ROOM_POINT["latitude"]
        longitude = self.cleaned_data.get("longitude") or DEFAULT_ROOM_POINT["longitude"]
        room.location = Point(float(longitude), float(latitude), srid=4326)
        if commit:
            room.save()
            self.save_m2m()
        return room


class LandlordRoomImageForm(forms.ModelForm):
    class Meta:
        model = RoomImage
        fields = ("image", "caption", "is_cover", "sort_order")
        labels = {
            "image": "Ảnh phòng",
            "caption": "Chú thích",
            "is_cover": "Đặt làm ảnh bìa",
            "sort_order": "Thứ tự hiển thị",
        }
        help_texts = {
            "image": "Hỗ trợ JPG, PNG, WebP. Ảnh chủ trọ sẽ hiển thị ngay sau khi tải lên.",
            "caption": "Ví dụ: Góc bếp, cửa sổ, nhà vệ sinh riêng.",
            "sort_order": "Số nhỏ hơn sẽ hiển thị trước.",
        }
        widgets = {
            "image": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
            "caption": forms.TextInput(attrs={"placeholder": "Góc phòng có cửa sổ"}),
            "sort_order": forms.NumberInput(attrs={"min": "0", "step": "1"}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        validate_room_image_upload(image)
        return image


class LandlordRoomImageMetaForm(forms.ModelForm):
    class Meta:
        model = RoomImage
        fields = ("caption", "sort_order")
        labels = {
            "caption": "Chú thích",
            "sort_order": "Thứ tự",
        }
        widgets = {
            "caption": forms.TextInput(attrs={"placeholder": "Góc phòng có cửa sổ"}),
            "sort_order": forms.NumberInput(attrs={"min": "0", "step": "1"}),
        }


class RejectRoomForm(forms.Form):
    reason = forms.CharField(label="Lý do từ chối", widget=forms.Textarea)


class RejectImageForm(forms.Form):
    moderation_note = forms.CharField(label="Lý do từ chối", widget=forms.Textarea)

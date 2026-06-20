from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0003_alter_room_gender_policy_alter_room_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="location_label",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="room",
            name="location_query",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="room",
            name="location_status",
            field=models.CharField(
                choices=[
                    ("unverified", "Chưa xác định"),
                    ("geocoded", "Đã ghim bản đồ"),
                    ("failed", "Không tìm thấy vị trí"),
                ],
                default="unverified",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="room",
            index=models.Index(fields=["location_status"], name="room_location_status_idx"),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("roommates", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="roommatepost",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Bản nháp"),
                    ("active", "Đang hiển thị"),
                    ("closed", "Đã đóng"),
                    ("expired", "Hết hạn"),
                    ("rejected", "Bị từ chối"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="roommatepost",
            name="type",
            field=models.CharField(
                choices=[
                    ("has_room", "Đã có phòng"),
                    ("looking_together", "Tìm bạn cùng thuê"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="roommatepost",
            name="gender_preference",
            field=models.CharField(
                choices=[
                    ("any", "Không yêu cầu"),
                    ("male", "Nam"),
                    ("female", "Nữ"),
                    ("same", "Cùng giới"),
                ],
                default="any",
                max_length=10,
            ),
        ),
    ]

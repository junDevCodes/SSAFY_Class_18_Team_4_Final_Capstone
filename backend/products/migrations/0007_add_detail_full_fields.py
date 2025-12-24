from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_merge_20251208_1750'),
    ]

    operations = [
        migrations.AddField(
            model_name='productdetail',
            name='full_image_description',
            field=models.JSONField(blank=True, default=list, null=True, verbose_name='상세 이미지 리스트', help_text='본문 설명 영역의 이미지 URL 목록'),
        ),
        migrations.AddField(
            model_name='productdetail',
            name='full_text_description',
            field=models.TextField(blank=True, null=True, verbose_name='상세 텍스트 설명', help_text='본문 설명 영역의 텍스트'),
        ),
    ]


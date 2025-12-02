# Generated manually for guest order support
# 비회원 주문 지원을 위한 필드 추가

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # user 필드를 nullable로 변경
        migrations.AlterField(
            model_name='order',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name='orders',
                to=settings.AUTH_USER_MODEL,
                verbose_name='주문자',
            ),
        ),
        # 비회원 이메일 필드 추가
        migrations.AddField(
            model_name='order',
            name='guest_email',
            field=models.EmailField(
                blank=True,
                max_length=254,
                null=True,
                verbose_name='비회원 이메일',
            ),
        ),
        # 비회원 이름 필드 추가
        migrations.AddField(
            model_name='order',
            name='guest_name',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name='비회원 이름',
            ),
        ),
        # 비회원 연락처 필드 추가
        migrations.AddField(
            model_name='order',
            name='guest_phone',
            field=models.CharField(
                blank=True,
                max_length=20,
                null=True,
                verbose_name='비회원 연락처',
            ),
        ),
    ]

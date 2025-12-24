from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0002_add_admin_category_daily"),
    ]

    operations = [
        migrations.AddField(
            model_name="adminbizdaily",
            name="is_test",
            field=models.BooleanField(
                default=False,
                verbose_name="테스트 데이터 여부",
            ),
        ),
        migrations.AddField(
            model_name="adminbizdaily",
            name="scenario",
            field=models.CharField(
                max_length=50,
                blank=True,
                null=True,
                verbose_name="시나리오 태그",
            ),
        ),
        migrations.AddField(
            model_name="admincategorydaily",
            name="is_test",
            field=models.BooleanField(
                default=False,
                verbose_name="테스트 데이터 여부",
            ),
        ),
        migrations.AddField(
            model_name="adminrecodaily",
            name="is_test",
            field=models.BooleanField(
                default=False,
                verbose_name="테스트 데이터 여부",
            ),
        ),
    ]



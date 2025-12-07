# Generated manually for price history optimization

from django.db import migrations, models


class Migration(migrations.Migration):
    """가격 히스토리 테이블 최적화 마이그레이션

    변경 사항:
    1. is_current 필드 추가: 현재 유효 가격 여부 (빠른 조회용)
    2. previous_price 필드 추가: 이전 가격 (변동폭 계산용)
    3. price_change 필드 추가: 가격 변동액 (이전 대비)
    4. price_change_rate 필드 추가: 가격 변동률 (%)
    5. 복합 유니크 제약: (product, recorded_at) - 같은 시점 중복 방지
    6. 부분 인덱스: is_current=True인 레코드만 인덱싱
    """

    dependencies = [
        ('products', '0003_seller_cascade_to_protect'),
    ]

    operations = [
        # 1. is_current 필드 추가 (현재 유효 가격 여부)
        migrations.AddField(
            model_name='productpricehistory',
            name='is_current',
            field=models.BooleanField(
                default=False,
                verbose_name='현재 가격 여부',
                help_text='True면 현재 유효한 가격 (상품당 하나만 True)',
                db_index=True,
            ),
        ),

        # 2. previous_price 필드 추가 (이전 가격)
        migrations.AddField(
            model_name='productpricehistory',
            name='previous_price',
            field=models.IntegerField(
                null=True,
                blank=True,
                verbose_name='이전 가격',
                help_text='변경 전 가격 (첫 기록은 NULL)',
            ),
        ),

        # 3. price_change 필드 추가 (가격 변동액)
        migrations.AddField(
            model_name='productpricehistory',
            name='price_change',
            field=models.IntegerField(
                null=True,
                blank=True,
                verbose_name='가격 변동액',
                help_text='현재가격 - 이전가격 (양수=인상, 음수=인하)',
            ),
        ),

        # 4. price_change_rate 필드 추가 (가격 변동률)
        migrations.AddField(
            model_name='productpricehistory',
            name='price_change_rate',
            field=models.DecimalField(
                max_digits=8,
                decimal_places=2,
                null=True,
                blank=True,
                verbose_name='가격 변동률',
                help_text='변동률 % (양수=인상, 음수=인하)',
            ),
        ),

        # 5. 현재 가격 빠른 조회를 위한 부분 인덱스
        # PostgreSQL: WHERE is_current = true 조건부 인덱스
        migrations.AddIndex(
            model_name='productpricehistory',
            index=models.Index(
                fields=['product', 'is_current'],
                name='ix_price_hist_current',
            ),
        ),

        # 6. 가격 변동 분석용 인덱스 (날짜 범위 쿼리)
        migrations.AddIndex(
            model_name='productpricehistory',
            index=models.Index(
                fields=['product', 'recorded_at', 'price'],
                name='ix_price_hist_analysis',
            ),
        ),

        # 7. 기존 데이터 마이그레이션: 각 상품의 최신 레코드를 is_current=True로 설정
        migrations.RunSQL(
            sql="""
            UPDATE product_price_histories pph
            SET is_current = TRUE
            WHERE pph.id = (
                SELECT pph2.id
                FROM product_price_histories pph2
                WHERE pph2.product_id = pph.product_id
                ORDER BY pph2.recorded_at DESC
                LIMIT 1
            );
            """,
            reverse_sql="""
            UPDATE product_price_histories SET is_current = FALSE;
            """,
        ),
    ]

// 포맷팅 유틸리티 함수

/**
 * 가격을 한국 원화 형식으로 포맷팅
 * @param val 가격 (숫자)
 * @returns 포맷팅된 가격 문자열 (예: "39,900원")
 */
export const formatPrice = (val: number): string => {
  return new Intl.NumberFormat('ko-KR').format(val) + '원'
}


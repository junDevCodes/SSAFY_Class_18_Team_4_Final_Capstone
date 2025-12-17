// 상수 정의

// API Base URL
// 프로덕션: 빈 문자열 → 상대 경로 사용 (Nginx 프록시)
// 로컬 개발: .env 파일에서 VITE_API_BASE_URL=http://localhost:8000 설정
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// 카테고리 목록 (상단 탭 등에서 사용)
export const CATEGORIES = [
  "추천",
  "베스트",
  "신상품",
  "비건",
  "정육",
  "수산",
  "베이커리",
] as const;

// 홈플러스 카테고리 아이콘 S3 기본 경로
// 파일명은 크롤링 카테고리 이름과 동일하며, 모두 .jpg 확장자를 사용한다.
// 예) BEAN_EGG → https://self-json-backup.s3.ap-northeast-2.amazonaws.com/homeplus/category_icon/BEAN_EGG.jpg
const CATEGORY_ICON_BASE_URL =
  "https://self-json-backup.s3.ap-northeast-2.amazonaws.com/homeplus/category_icon";

// 카테고리 아이콘이 없을 때 사용할 기본 이미지 (fallback)
const DEFAULT_CATEGORY_IMAGE =
  "https://images.unsplash.com/photo-1542838132-92c53300491e?q=80&w=300&auto=format&fit=crop";

// SelF 카테고리 이름 → 크롤링 서비스 카테고리 코드 매핑
// 프론트에서 사용하는 한글 카테고리명을 크롤링 기준 카테고리 코드(예: BEAN_EGG)로 매핑한다.
const CATEGORY_NAME_TO_SERVICE_CODE: Record<string, string> = {

  "과일": "FRUIT",

  "쌀/잡곡": "GRAIN",

  "면/가루/베이커리/제빵": "NOODLE_FLOUR",

  "채소/샐러드/버섯/나물": "VEGETABLE",

  "두부/콩/계란": "BEAN_EGG",

  "육류": "MEAT",

  "수산물/해산물/건어물": "SEAFOOD",

  "우유/유제품": "DAIRY",

  "김치/반찬/절임": "KIMCHI_SIDE",

  "양념/조미/소스/오일": "SEASONING_SAUCE_OIL",

  "견과/건과/간식": "NUT_DRY_ETC",

  "음료": "DRINK",

  "라면/간편식품/통조림": "INSTANT_FOOD",
};

// 카테고리 이름으로 S3 아이콘 URL 반환
export function getCategoryImage(name: string): string {
  // 이름이 비어 있으면 기본 이미지 반환
  const n = (name || "").trim();
  if (!n) return DEFAULT_CATEGORY_IMAGE;

  // 한글 카테고리명을 크롤링 카테고리 코드로 매핑
  const serviceCode = CATEGORY_NAME_TO_SERVICE_CODE[n];
  if (!serviceCode) {
    return DEFAULT_CATEGORY_IMAGE;
  }

  // 최종 URL 생성 (예: BEAN_EGG → .../BEAN_EGG.jpg)
  return `${CATEGORY_ICON_BASE_URL}/${serviceCode}.jpg`;
}

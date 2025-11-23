// 상수 정의

// API Base URL
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// 카테고리 목록
export const CATEGORIES = ['추천', '베스트', '신상품', '비건', '정육', '수산', '베이커리'] as const

// 빠른 카테고리
export const QUICK_CATEGORIES = [
  { name: '채소', image: 'https://images.unsplash.com/photo-1550989460-0adf9ea622e2?q=80&w=300&auto=format&fit=crop' },
  { name: '과일', image: 'https://images.unsplash.com/photo-1610832958506-aa56368176cf?q=80&w=300&auto=format&fit=crop' },
  { name: '정육', image: 'https://images.unsplash.com/photo-1588168333986-5078d3ae3976?q=80&w=300&auto=format&fit=crop' },
  { name: '수산', image: 'https://images.unsplash.com/photo-1534604973900-c43ab4c2e0ab?q=80&w=300&auto=format&fit=crop' },
  { name: '샐러드', image: 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=300&auto=format&fit=crop' },
  { name: '면/양념', image: 'https://images.unsplash.com/photo-1552611052-33e04de081de?q=80&w=300&auto=format&fit=crop' },
  { name: '음료', image: 'https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?q=80&w=300&auto=format&fit=crop' },
  { name: '간식', image: 'https://images.unsplash.com/photo-1558961363-fa8fdf82db35?q=80&w=300&auto=format&fit=crop' },
  { name: '베이커리', image: 'https://images.unsplash.com/photo-1586444248902-2f64eddc13df?q=80&w=300&auto=format&fit=crop' },
  { name: '생활', image: 'https://images.unsplash.com/photo-1583947215259-38e31be8751f?q=80&w=300&auto=format&fit=crop' }
] as const

// 카테고리 이름 -> 이미지 매핑 (키워드 기반)
const CATEGORY_IMAGE_RULES: Array<{ match: RegExp, image: string }> = [
  { match: /채소|야채/, image: 'https://images.unsplash.com/photo-1550989460-0adf9ea622e2?q=80&w=300&auto=format&fit=crop' },
  { match: /과일|견과/, image: 'https://images.unsplash.com/photo-1610832958506-aa56368176cf?q=80&w=300&auto=format&fit=crop' },
  { match: /정육|육류|고기/, image: 'https://images.unsplash.com/photo-1588168333986-5078d3ae3976?q=80&w=300&auto=format&fit=crop' },
  { match: /수산|해산|수산물|생선|해물/, image: 'https://images.unsplash.com/photo-1534604973900-c43ab4c2e0ab?q=80&w=300&auto=format&fit=crop' },
  { match: /샐러드|샐럿/, image: 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=300&auto=format&fit=crop' },
  { match: /면|양념|라면|파스타|소스/, image: 'https://images.unsplash.com/photo-1552611052-33e04de081de?q=80&w=300&auto=format&fit=crop' },
  { match: /음료|주스|커피|차/, image: 'https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?q=80&w=300&auto=format&fit=crop' },
  { match: /간식|과자|스낵|디저트/, image: 'https://images.unsplash.com/photo-1558961363-fa8fdf82db35?q=80&w=300&auto=format&fit=crop' },
  { match: /베이커리|빵|케이크|베이/, image: 'https://images.unsplash.com/photo-1586444248902-2f64eddc13df?q=80&w=300&auto=format&fit=crop' },
  { match: /생활|리빙|주방|세제/, image: 'https://images.unsplash.com/photo-1583947215259-38e31be8751f?q=80&w=300&auto=format&fit=crop' },
  { match: /냉동|냉동식품|아이스/, image: 'https://images.unsplash.com/photo-1585238342029-6473e3ce52d1?q=80&w=300&auto=format&fit=crop' },
  { match: /우유|유제품|치즈|요거트/, image: 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?q=80&w=300&auto=format&fit=crop' },
  { match: /밀키트|간편식|HMR|밀키/, image: 'https://images.unsplash.com/photo-1544025162-d76694265947?q=80&w=300&auto=format&fit=crop' },
]

const DEFAULT_CATEGORY_IMAGE = 'https://images.unsplash.com/photo-1542838132-92c53300491e?q=80&w=300&auto=format&fit=crop'

// 카테고리 이름으로 이미지 반환
export function getCategoryImage(name: string): string {
  const n = (name || '').trim()
  for (const rule of CATEGORY_IMAGE_RULES) {
    if (rule.match.test(n)) return rule.image
  }
  return DEFAULT_CATEGORY_IMAGE
}


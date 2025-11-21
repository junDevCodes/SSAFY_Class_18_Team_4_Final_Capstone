import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Product } from '@/types/product'

// 상품 스토어
export const useProductStore = defineStore('products', () => {
  const products = ref<Product[]>([
    { id: 101, name: "무항생제 1등급 한우 등심 200g", price: 39900, originalPrice: 45000, discount: 11, isBest: true, image: "https://images.unsplash.com/photo-1603048297172-c92544798d5e?q=80&w=1000&auto=format&fit=crop", desc: "입안에서 살살 녹는 마블링" },
    { id: 102, name: "GAP 인증 경북 영주 사과 1.5kg", price: 12900, originalPrice: 15900, discount: 19, isBest: true, image: "https://images.unsplash.com/photo-1568702846914-96b305d2aaeb?q=80&w=1000&auto=format&fit=crop", desc: "꿀이 꽉 찬 고당도" },
    { id: 103, name: "친환경 유기농 쌈채소 모듬", price: 4500, originalPrice: 4500, discount: 0, isBest: false, image: "https://images.unsplash.com/photo-1524593166156-312f362cada0?q=80&w=1000&auto=format&fit=crop", desc: "당일 수확 아삭한 식감" },
    { id: 104, name: "노르웨이 생연어 회/초밥용", price: 21900, originalPrice: 26000, discount: 15, isBest: true, image: "https://images.unsplash.com/photo-1599084993091-1a8066d53b4d?q=80&w=1000&auto=format&fit=crop", desc: "항공 직송 신선함" },
    { id: 105, name: "이탈리아 정통 발사믹 식초", price: 15000, originalPrice: 18000, discount: 16, isBest: false, image: "https://images.unsplash.com/photo-1565535810893-4103319c7757?q=80&w=1000&auto=format&fit=crop", desc: "샐러드의 품격" },
    { id: 106, name: "유기농 그릭 요거트 450g", price: 9900, originalPrice: 11000, discount: 10, isBest: true, image: "https://images.unsplash.com/photo-1488477181946-6428a0291777?q=80&w=1000&auto=format&fit=crop", desc: "꾸덕한 식감과 풍미" },
    { id: 107, name: "제주 흑돼지 삼겹살 구이용", price: 18900, originalPrice: 22000, discount: 14, isBest: true, image: "https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?q=80&w=1000&auto=format&fit=crop", desc: "쫄깃한 육질" },
    { id: 108, name: "샤인머스캣 2kg (3수)", price: 29900, originalPrice: 35000, discount: 14, isBest: true, image: "https://images.unsplash.com/photo-1596694646871-3a560460708a?q=80&w=1000&auto=format&fit=crop", desc: "망고향 가득 프리미엄" },
    { id: 109, name: "아보카도 4입 (멕시코산)", price: 8900, originalPrice: 12000, discount: 25, isBest: false, image: "https://images.unsplash.com/photo-1523049673856-3dbac7454855?q=80&w=1000&auto=format&fit=crop", desc: "숲속의 버터" },
  ])

  // TODO: API에서 상품 목록 가져오기
  const fetchProducts = async () => {
    // API 호출 로직
  }

  return {
    products,
    fetchProducts
  }
})


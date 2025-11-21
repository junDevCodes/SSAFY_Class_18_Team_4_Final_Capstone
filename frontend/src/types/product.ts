// 상품 타입 정의
export interface Product {
  id: number
  name: string
  price: number
  originalPrice: number
  discount: number
  isBest: boolean
  image: string
  desc: string
}

export interface CartItem extends Product {
  qty: number
}


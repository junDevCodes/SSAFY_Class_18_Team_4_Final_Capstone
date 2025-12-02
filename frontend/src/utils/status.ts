// 주문/결제 상태 텍스트 및 스타일 유틸

// 주문 상태 텍스트 매핑
export const getOrderStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    pending: '주문 접수',
    paid: '결제 완료',
    processing: '준비중',
    shipped: '배송중',
    delivered: '배송 완료',
    cancelled: '취소',
    refunded: '환불',
  }
  return statusMap[status] || status
}

// 결제 상태 텍스트 매핑
export const getPaymentStatusText = (status: string | null | undefined): string => {
  if (!status) return '정보 없음'
  const statusMap: Record<string, string> = {
    pending: '대기중',
    success: '결제 완료',
    failed: '실패',
    cancelled: '취소',
    refunded: '환불',
  }
  return statusMap[status] || status
}


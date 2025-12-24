export type Celebrity = 'CHA_EUNWOO' | 'KARINA'

type StepKey = '3' | '4' | '5' | '6' | '7'

type CelebLine = {
  question: string
  reaction: string
  ending: string
}

export const CELEB_LINES: Record<Celebrity, Record<StepKey, CelebLine>> = {
  CHA_EUNWOO: {
    '3': {
      question: '같이 고르자. 혹시 정말 못 먹는 음식이 있어?',
      reaction: '알려줘서 고마워. 그건 추천에서 살짝 빼둘게.',
      ending: '취향을 더 잘 알게 됐어. 계속 같이 골라볼까?',
    },
    '4': {
      question: '최근에 자주 찾게 되는 맛이나 향이 있어?',
      reaction: '좋아, 그 느낌에 맞춰서 준비해볼게.',
      ending: '조금씩 더 가까워지고 있어.',
    },
    '5': {
      question: '오늘은 어떤 기분이야? 어떤 식재료를 고르고 싶어?',
      reaction: '그렇구나. 그 기분에 어울리게 고른거구나',
      ending: '분위기에 맞는 조합을 생각해볼게.',
    },
    '6': {
      question: '또 좋아하는거 있어? 솔직하게.',
      reaction: '알겠어. 시간에 맞춰서 추천을 조정할게.',
      ending: '이제 거의 완성됐어. 조금만 더 함께 해보자.',
    },
    '7': {
      question: '마지막으로 꼭 챙기고 싶은 포인트가 있을까?',
      reaction: '좋아요. 그 포인트를 중심으로 마무리해볼게.',
      ending: '고마워. 이제 너만의 추천을 준비해둘게.',
    },
  },
  KARINA: {
    '3': {
      question: '바로 물어볼게. 절대 싫은 음식 있어?',
      reaction: '오케이, 그건 리스트에서 깔끔하게 제외할게.',
      ending: '좋아, 취향 확실히 이해했어.',
    },
    '4': {
      question: '요즘 꽂힌 맛이나 향 있어? 딱 떠오르는 거.',
      reaction: '그 느낌 알지. 거기에 맞춰서 골라줄게.',
      ending: '점점 너 취향대로 맞춰지고 있어.',
    },
    '5': {
      question: '오늘 텐션은 어떤게 좋아? 편하게 말해줘.',
      reaction: '그럼 그 분위기에 맞게 고른거구나.',
      ending: '조합이 슬슬 그림 나오는 중.',
    },
    '6': {
      question: '또 좋아하는거 있어? 솔직하게.',
      reaction: '오케이, 좋았어.',
      ending: '거의 다 왔어. 조금만 더 가자.',
    },
    '7': {
      question: '마지막 체크포인트 있어? 놓치면 아쉬운 거.',
      reaction: '바로 반영할게. 깔끔하게 끝내자.',
      ending: '끝! 이걸로 너 전용 추천 세팅 완료.',
    },
  },
} as const

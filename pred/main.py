from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SelF Pred API", version="1.0.0")

# CORS 설정 (배포 시 Backend 도메인만 허용하도록 조정 필요)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    """루트 경로 응답"""
    return {"message": "SelF Pred API", "status": "running"}


@app.get("/health")
def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}


@app.post("/api/recommend")
async def recommend_products():
    """추천 로직 자리 - 추후 구현"""
    # TODO: 추천 로직 추가
    return {"status": "pending"}


@app.post("/api/predict-price")
async def predict_price():
    """가격 예측 로직 자리 - 추후 구현"""
    # TODO: 가격 예측 로직 추가
    return {"status": "pending"}

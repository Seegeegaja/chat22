from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chat_utils import load_faiss, ask_question

app = FastAPI(title="초콜릿 챗봇 API")

# ✅ CORS 설정 (모든 도메인 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영 환경에서는 도메인 지정 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✅ 질문 요청 모델
class Question(BaseModel):
    query: str


# ✅ 글로벌 DB 객체
db = None


# ✅ 서버 시작 시 FAISS 로드
@app.on_event("startup")
def startup_event():
    global db
    db = load_faiss()
    print("✅ FAISS DB 로딩 완료")


# ✅ 테스트용 루트 경로
@app.get("/")
def root():
    return {"message": "초콜릿 챗봇 서버가 실행 중입니다."}


# ✅ 질문 처리 API
@app.post("/ask")
async def handle_question(q: Question):
    if not db:
        return {"error": "FAISS 데이터베이스가 로드되지 않았습니다."}

    answer = ask_question(q.query, db)
    return {
        "question": q.query,
        "answer": answer
    }

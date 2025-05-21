import os
import random
import json
import mysql.connector
from dotenv import load_dotenv

# LangChain 관련
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import Document
from langchain.chains import LLMChain, StuffDocumentsChain, RetrievalQA
from langchain_core.prompts import PromptTemplate

# 환경 변수 로드
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
faiss_dir = "faiss_products_db"

if not openai_api_key:
    raise ValueError("❌ .env 파일에 OPENAI_API_KEY가 없습니다.")

# ✅ FAISS 로드 함수
def load_faiss():
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    return FAISS.load_local(faiss_dir, embeddings, allow_dangerous_deserialization=True)

# ✅ 문자열 안전 처리
def safe_str(value):
    return str(value) if value is not None else "정보 없음"

# ✅ FAQ 문서 생성
def generate_faq_documents(n=300):
    sample_questions = [
        "이 초콜릿은 어디서 생산되나요?",
        "가장 인기 있는 제품은 무엇인가요?",
        "유통기한이 긴 제품은 어떤 것이 있나요?",
        "비건 초콜릿이 있나요?",
        "브랜드별 특징을 알려주세요.",
        "무설탕 제품이 있나요?",
        "가격대가 저렴한 브랜드는 어떤 것인가요?",
        "다크 초콜릿은 어떤 제품이 있나요?",
        "선물용으로 적합한 제품은?",
        "어린이에게 추천할 만한 초콜릿은?"
    ]
    faq_docs = []
    for i in range(n):
        question = random.choice(sample_questions)
        answer = f"{question}에 대한 정보는 제품 상세 설명에서 확인하실 수 있습니다."
        content = f"❓ 질문: {question}\n📝 답변: {answer}"
        faq_docs.append(Document(
            page_content=content,
            metadata={
                "type": "faq",
                "faq_id": i + 1,
                "category": "일반"
            }
        ))
    return faq_docs

# ✅ FAQ JSON 파일로 저장
def save_faqs_to_json(docs, filename="faqs.json"):
    faq_json = []
    for doc in docs:
        if doc.metadata.get("type") == "faq":
            lines = doc.page_content.split('\n')
            question_line = lines[0] if len(lines) > 0 else ""
            answer_line = lines[1] if len(lines) > 1 else ""
            faq_json.append({
                "question": question_line.replace("❓ 질문: ", "").strip(),
                "answer": answer_line.replace("📝 답변: ", "").strip(),
                "metadata": doc.metadata
            })

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(faq_json, f, ensure_ascii=False, indent=2)
    print(f"✅ {filename} 파일로 FAQ 저장 완료!")

# ✅ MySQL에서 제품/브랜드 정보 로드
def load_products_from_mysql():
    conn = mysql.connector.connect(
        host="awseb-e-ywnmbap8x2-stack-awsebrdsdatabase-ul7iljewboaj.c0vo2ike8h6l.us-east-1.rds.amazonaws.com",
        user="chocoworld",
        password="chocoworld",
        database="chocoworld"
    )
    cursor = conn.cursor()
    documents = []

    cursor.execute("""
        SELECT 
            p.title, p.content, p.price, p.stock, p.materials, p.explamation_date,
            p.weight, p.origin, p.category, p.brand_id,
            b.title AS brand_title, b.introduction AS brand_intro
        FROM product p
        LEFT JOIN brand b ON p.brand_id = b.id
    """)
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()

    for row in rows:
        data = dict(zip(columns, row))
        product_text = f"""
🍫 [제품 정보]
- 제품명: {safe_str(data['title'])}
- 카테고리: {safe_str(data['category'])}
- 원산지: {safe_str(data['origin'])}
- 가격: {safe_str(data['price'])}원
- 재고: {safe_str(data['stock'])}개
- 무게: {safe_str(data['weight'])}
- 유통기한: {safe_str(data['explamation_date'])}
- 재료: {safe_str(data['materials'])}

📄 설명:
{safe_str(data['content'])}

🏷️ 브랜드:
- 브랜드명: {safe_str(data['brand_title'])}
- 소개: {safe_str(data['brand_intro'])}
""".strip()

        documents.append(Document(
            page_content=product_text,
            metadata={
                "type": "product",
                "brand_id": data["brand_id"],
                "brand_name": data["brand_title"],
                "product_name": data["title"]
            }
        ))

    cursor.execute("""
        SELECT title, content, founded, office, representative, web_site, country, introduction, history
        FROM brand
    """)
    for row in cursor.fetchall():
        (
            title, content, founded, office, representative, website,
            country, introduction, history
        ) = row

        brand_text = f"""
🏷️ [브랜드 정보]
- 브랜드명: {safe_str(title)}
- 국가: {safe_str(country)}
- 설립: {safe_str(founded)}, 본사: {safe_str(office)}
- 대표 제품: {safe_str(representative)}
- 웹사이트: {safe_str(website)}

📄 브랜드 소개:
{safe_str(content)}

📜 브랜드 역사:
{safe_str(history)}

📝 요약:
{safe_str(introduction)}
""".strip()

        documents.append(Document(
            page_content=brand_text,
            metadata={
                "type": "brand",
                "brand_name": title
            }
        ))

    conn.close()
    return documents

# ✅ FAISS에 저장
def store_in_faiss(docs, path=faiss_dir):
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    db = FAISS.from_documents(docs, embeddings)
    db.save_local(path)
    print(f"✅ FAISS 인덱스 저장 완료 → {path}/")

# ✅ 질문 처리 함수 (FastAPI에서 사용)
# ✅ FAISS 로드 함수
def load_faiss():
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    return FAISS.load_local(faiss_dir, embeddings, allow_dangerous_deserialization=True)

# ✅ 전체 문서에서 브랜드 목록 직접 추출 (중복 제거)
def count_unique_brands(db):
    results = db.similarity_search_with_score("", k=1000)
    brand_names = set()
    for doc, _ in results:
        if doc.metadata.get("type") == "brand":
            brand = doc.metadata.get("brand_name")
            if brand:
                brand_names.add(brand.strip())
    return sorted(brand_names)

# ✅ 질문 처리 함수
def ask_question(question, db):
    llm = ChatOpenAI(model="gpt-4o", openai_api_key=openai_api_key)

    # ✅ 브랜드 목록 질문일 경우
    if any(keyword in question for keyword in ["브랜드 종류", "브랜드 뭐", "브랜드만", "브랜드 리스트"]):
        brand_list = count_unique_brands(db)
        if not brand_list:
            return "⚠️ 등록된 브랜드 정보를 찾을 수 없습니다."
        return f"현재 등록된 브랜드는 총 {len(brand_list)}개입니다:\n- " + "\n- ".join(brand_list)

    # ✅ 제품 이름만 묻는 질문
    elif "브랜드" not in question and any(keyword in question for keyword in ["제품명", "이름만", "리스트", "목록", "뭐 있어"]):
        retriever = db.as_retriever(search_kwargs={"k": 100})
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
당신은 초콜릿 제품 이름을 정리해주는 도우미입니다.

아래 정보를 참고하여 **제품명만** 목록으로 보여 주세요.

📦 제품 정보:
{context}

❓ 질문:
{question}

🧾 응답 (제품명만):
"""
        )
    # ✅ 일반 질문
    else:
        retriever = db.as_retriever(search_kwargs={"k": 15})
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
당신은 고급 초콜릿 전문 도우미입니다.

아래 제품 정보를 참고하여 **간결하고 품격 있는 문장**으로 사용자 질문에 답변해 주세요.

📦 제품 정보:
{context}

❓ 질문:
{question}

🧾 답변:
"""
        )

    # 공통 QA 체인
    llm_chain = LLMChain(llm=llm, prompt=prompt)
    stuff_chain = StuffDocumentsChain(llm_chain=llm_chain, document_variable_name="context")
    qa = RetrievalQA(retriever=retriever, combine_documents_chain=stuff_chain)
    return qa.run(question)

# ✅ 실행 스크립트
if __name__ == "__main__":

    product_docs = load_products_from_mysql()
    print(product_docs)

    print("🔄 FAQ 300개 생성 중...")
    faq_docs = generate_faq_documents(300)

    print("💾 FAQ를 JSON 파일로 저장 중...")
    save_faqs_to_json(faq_docs, "faqs.json")

    print("📦 FAISS에 저장할 문서 결합 중...")
    all_docs = product_docs + faq_docs

    print("📥 FAISS에 문서 저장 중...")
    store_in_faiss(all_docs)

    print("✅ 전체 작업 완료! 🎉")

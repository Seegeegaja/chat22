from chat_utils import load_products_from_mysql, store_in_faiss, load_faiss

if __name__ == "__main__":
    print("📦 제품과 브랜드 정보를 불러오는 중...")
    docs = load_products_from_mysql()
    print(f"📦 불러온 문서 개수: {len(docs)}개")

    print("🧠 FAISS 벡터 저장 중...")
    store_in_faiss(docs)
    print("✅ FAISS 인덱스 저장 완료!")

    print("\n🔄 인덱스 재불러오기 중...")
    db = load_faiss()

    print("\n🔍 FAISS 검색 테스트: '브랜드'")
    results = db.similarity_search("브랜드", k=5)
    print(f"🔎 검색된 문서 수: {len(results)}개")
    for i, doc in enumerate(results):
        print(f"\n📄 결과 {i+1}:")
        print(doc.page_content[:200])  # 앞부분만 출력

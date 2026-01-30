"""
Build Vector DB from MySQL Database.
Extracts text data from MySQL and creates ChromaDB embeddings for RAG search.

Usage:
    python src/build_vector_db_from_mysql.py [--reset]
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

import pymysql
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "esg")
DB_PORT = int(os.getenv("DB_PORT", 3306))

# Vector DB Configuration
VECTOR_DB_DIR = Path(__file__).parent.parent / "vector_db"
COLLECTION_NAME = "esg_documents"
EMBEDDING_MODEL_NAME = "BAAI/bge-m3"

# Chunking Configuration
CHUNK_SIZE = 500  # characters per chunk
CHUNK_OVERLAP = 50  # overlap between chunks


def get_mysql_connection():
    """Connect to MySQL database."""
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        print(f"✅ MySQL 연결 성공: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        return conn
    except pymysql.MySQLError as e:
        print(f"❌ MySQL 연결 실패: {e}")
        sys.exit(1)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    if not text or len(text.strip()) == 0:
        return []
    
    text = text.strip()
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Avoid cutting in the middle of a word
        if end < len(text):
            # Find last space to avoid cutting words
            last_space = chunk.rfind(' ')
            if last_space > chunk_size // 2:
                chunk = chunk[:last_space]
                end = start + last_space
        
        if chunk.strip():
            chunks.append(chunk.strip())
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks


def fetch_documents_from_mysql(conn) -> List[Dict[str, Any]]:
    """Fetch all documents and their content from MySQL."""
    documents = []
    
    with conn.cursor() as cursor:
        # Get all documents
        cursor.execute("""
            SELECT id, filename, company_name, report_year 
            FROM documents
        """)
        docs = cursor.fetchall()
        
        print(f"\n📄 문서 {len(docs)}개 발견")
        
        for doc in docs:
            doc_id = doc['id']
            company = doc['company_name'] or 'Unknown'
            year = doc['report_year'] or 0
            filename = doc['filename']
            
            print(f"\n📖 처리 중: {filename} ({company}, {year})")
            
            # Get pages with markdown content
            cursor.execute("""
                SELECT id, page_no, full_markdown 
                FROM pages 
                WHERE doc_id = %s AND full_markdown IS NOT NULL
                ORDER BY page_no
            """, (doc_id,))
            pages = cursor.fetchall()
            
            print(f"   페이지 수: {len(pages)}")
            
            for page in pages:
                page_no = page['page_no']
                markdown = page['full_markdown']
                
                if not markdown or len(markdown.strip()) < 50:
                    continue
                
                # Chunk the markdown content
                chunks = chunk_text(markdown)
                
                for chunk_idx, chunk in enumerate(chunks):
                    documents.append({
                        'doc_id': doc_id,
                        'company_name': company,
                        'report_year': year,
                        'page_no': page_no,
                        'chunk_index': chunk_idx,
                        'content': chunk,
                        'source': f"{filename}#page{page_no}"
                    })
            
            # Also get table data as separate chunks
            cursor.execute("""
                SELECT dt.id, dt.page_no, dt.title, dt.table_index,
                       GROUP_CONCAT(tc.content SEPARATOR ' | ') as table_content
                FROM doc_tables dt
                LEFT JOIN table_cells tc ON tc.table_id = dt.id
                WHERE dt.doc_id = %s
                GROUP BY dt.id, dt.page_no, dt.title, dt.table_index
            """, (doc_id,))
            tables = cursor.fetchall()
            
            for table in tables:
                table_content = table['table_content']
                if not table_content or len(table_content.strip()) < 20:
                    continue
                
                # Add table title if available
                title = table['title'] or ''
                full_content = f"{title}\n{table_content}" if title else table_content
                table_idx = table['table_index'] or table['id']  # Use table_index or id for uniqueness
                
                documents.append({
                    'doc_id': doc_id,
                    'company_name': company,
                    'report_year': year,
                    'page_no': table['page_no'],
                    'chunk_index': 0,
                    'table_id': table_idx,  # Add table ID for uniqueness
                    'content': full_content[:CHUNK_SIZE * 2],  # Tables can be longer
                    'source': f"{filename}#page{table['page_no']}#table{table_idx}",
                    'content_type': 'table'
                })
    
    print(f"\n✅ 총 {len(documents)}개 청크 생성됨")
    return documents


def build_vector_db(documents: List[Dict[str, Any]], reset: bool = False):
    """Build ChromaDB from documents."""
    
    # Create/Reset vector DB directory
    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📦 Vector DB 디렉토리: {VECTOR_DB_DIR}")
    
    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    
    # Delete existing collection if reset
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"🗑️  기존 컬렉션 '{COLLECTION_NAME}' 삭제됨")
        except Exception:
            pass
    
    # Create collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    
    print(f"📁 컬렉션: {COLLECTION_NAME}")
    print(f"   현재 문서 수: {collection.count()}")
    
    if not documents:
        print("⚠️  임베딩할 문서가 없습니다.")
        return
    
    # Load embedding model
    print(f"\n🤖 임베딩 모델 로딩: {EMBEDDING_MODEL_NAME}")
    print("   (처음 실행 시 모델 다운로드에 시간이 걸릴 수 있습니다...)")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    # Prepare data for ChromaDB
    ids = []
    texts = []
    metadatas = []
    
    for idx, doc in enumerate(documents):
        doc_id = f"{doc['company_name']}_{doc['report_year']}_p{doc['page_no']}_c{doc['chunk_index']}"
        if doc.get('content_type') == 'table':
            table_id = doc.get('table_id', idx)
            doc_id = f"{doc['company_name']}_{doc['report_year']}_p{doc['page_no']}_t{table_id}"
        
        ids.append(doc_id)
        texts.append(doc['content'])
        metadatas.append({
            'company_name': doc['company_name'],
            'report_year': doc['report_year'],
            'page_no': doc['page_no'],
            'chunk_index': doc['chunk_index'],
            'source': doc['source'],
            'content_type': doc.get('content_type', 'text')
        })
    
    # Generate embeddings in batches
    print(f"\n🔄 {len(texts)}개 청크 임베딩 생성 중...")
    batch_size = 32
    
    for i in range(0, len(texts), batch_size):
        batch_end = min(i + batch_size, len(texts))
        batch_texts = texts[i:batch_end]
        batch_ids = ids[i:batch_end]
        batch_metadatas = metadatas[i:batch_end]
        
        # Generate embeddings
        embeddings = model.encode(batch_texts, show_progress_bar=False).tolist()
        
        # Add to collection
        collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=batch_metadatas
        )
        
        progress = min(batch_end, len(texts))
        print(f"   진행률: {progress}/{len(texts)} ({100*progress//len(texts)}%)")
    
    print(f"\n✅ Vector DB 구축 완료!")
    print(f"   총 문서 수: {collection.count()}")
    print(f"   저장 위치: {VECTOR_DB_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Build Vector DB from MySQL")
    parser.add_argument("--reset", action="store_true", help="Reset existing vector DB")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 MySQL → Vector DB 변환 시작")
    print("=" * 60)
    
    # Connect to MySQL
    conn = get_mysql_connection()
    
    try:
        # Fetch documents
        documents = fetch_documents_from_mysql(conn)
        
        # Build Vector DB
        build_vector_db(documents, reset=args.reset)
        
    finally:
        conn.close()
    
    print("\n" + "=" * 60)
    print("🎉 완료! 이제 백엔드 API에서 검색을 사용할 수 있습니다.")
    print("=" * 60)


if __name__ == "__main__":
    main()

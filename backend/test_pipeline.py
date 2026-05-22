import os
from reportlab.pdfgen import canvas

# Import pipeline modules
from app.ingestion.pdf_loader import load_pdf
from app.ingestion.chunker import split_text
from app.embeddings.embedder import create_embeddings
from app.vectordb.chroma_store import ChromaStore
from app.graph.entity_extractor import EntityExtractor
from app.graph.neo4j_store import Neo4jStore
from app.retrieval.retriever import SemanticRetriever
from app.retrieval.graph_retriever import GraphRetriever
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.context_builder import ContextBuilder
from app.llm.generator import AnswerGenerator

def create_sample_pdf(file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    c = canvas.Canvas(file_path)
    text = c.beginText(40, 800)
    
    content = [
        "Diabetes and Kidney Disease: A Comprehensive Study.",
        "",
        "Diabetes mellitus is a chronic metabolic disorder characterized by high blood sugar levels.",
        "Over time, uncontrolled diabetes can lead to severe complications, including diabetic nephropathy.",
        "Diabetic nephropathy is a leading cause of chronic kidney disease and end-stage renal disease.",
        "Early detection and strict glycemic control are essential to prevent or delay the onset of kidney damage.",
        "Treatment often involves managing blood pressure, using ACE inhibitors, and lifestyle modifications.",
    ]
    
    for line in content:
        text.textLine(line)
        
    c.drawText(text)
    c.save()

def main():
    pdf_path = "data/sample.pdf"
    
    print("\n--- GRAPHRAG KNOWLEDGE INGESTION ---")
    create_sample_pdf(pdf_path)
    text = load_pdf(pdf_path)
    chunks = split_text(text)
    embeddings = create_embeddings(chunks)
    
    # Init Stores
    store = ChromaStore(path="data/chroma", collection_name="medical_test")
    store.add_chunks(chunks=chunks, embeddings=embeddings)
    
    extractor = EntityExtractor()
    neo4j_store = Neo4jStore()
    
    print("[*] Ingestion pipeline complete.")

    print("\n--- PHASE 3: TRUE GRAPHRAG RETRIEVAL & GENERATION ---")
    
    # Init Retrievers
    semantic_retriever = SemanticRetriever(store=store)
    graph_retriever = GraphRetriever(neo4j_store=neo4j_store, extractor=extractor)
    hybrid_retriever = HybridRetriever(semantic_retriever=semantic_retriever, graph_retriever=graph_retriever)
    
    query_text = "How does diabetes affect kidneys and what treatments help?"
    print(f"Query: '{query_text}'")
    
    # 1. Retrieve Hybrid Evidence
    print("\n[*] Retrieving Hybrid Evidence...")
    hybrid_results = hybrid_retriever.retrieve(query=query_text, top_k=2)
    
    # 2. Build Context
    print("[*] Assembling Context...")
    builder = ContextBuilder()
    orchestrated_context = builder.build_context(hybrid_results)
    
    print("\n================== ORCHESTRATED CONTEXT ==================")
    print(orchestrated_context)
    print("==========================================================")
    
    # 3. LLM Generation
    print("\n[*] Generating Answer using Evidence...")
    generator = AnswerGenerator()
    final_answer = generator.generate_answer(query=query_text, context=orchestrated_context)
    
    print("\n====================== FINAL ANSWER ======================")
    print(final_answer)
    print("==========================================================")

if __name__ == "__main__":
    main()

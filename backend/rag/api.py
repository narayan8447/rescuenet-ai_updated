from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from backend.rag.models import RAGQuery, RAGResponse
from backend.rag.rag_engine import rag_engine

router = APIRouter(prefix="/api/rag", tags=["RAG Knowledge Base"])

@router.post("/search", response_model=RAGResponse)
def search_knowledge_base(query: RAGQuery):
    """
    Query the authoritative disaster knowledge base.
    Uses Hybrid Search + Cross-Encoder Re-ranking to ensure high precision.
    """
    try:
        # Step 1: Query Expansion via LLM
        from backend.rag.rag_engine import get_llm
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = get_llm()
        expansion_prompt = "You are an emergency response expert. Expand the following user query with related disaster management keywords, FEMA protocols, or synonyms to improve vector search recall. Reply ONLY with the expanded query string, no other text."
        try:
            import os
            if os.environ.get("GROQ_API_KEY", "dummy_key") == "dummy_key":
                raise ValueError("Dummy key")
            expanded = llm.invoke([SystemMessage(content=expansion_prompt), HumanMessage(content=query.query)]).content
            # Combine original and expanded for maximum semantic surface area
            query.query = f"{query.query} {expanded}"
        except Exception:
            pass # Fallback to original query if LLM fails
            
        # Step 2: Retrieve
        response = rag_engine.retrieve(query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest")
def ingest_documents(documents: List[Dict[str, Any]]):
    """
    Ingest a batch of documents into the knowledge base.
    Documents must have 'text' and optional 'metadata'.
    """
    try:
        rag_engine.ingest_documents(documents)
        return {"status": "success", "message": f"Ingested {len(documents)} chunks."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

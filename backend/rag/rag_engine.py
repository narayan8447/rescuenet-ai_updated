import os
import uuid
import time
import math
from typing import List, Dict, Any, Optional
import re
import hashlib
from rank_bm25 import BM25Okapi

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import requests
import numpy as np

try:
    if os.environ.get("RENDER") is not None:
        raise ImportError("Forcing API mode on Render to save memory")
    from sentence_transformers import SentenceTransformer, CrossEncoder
    HAS_LOCAL_MODELS = True
except ImportError:
    HAS_LOCAL_MODELS = False

from backend.core.llm_pool import get_openrouter_llm, parse_llm_json
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools import DuckDuckGoSearchRun
from pydantic import BaseModel, Field

from backend.rag.models import DocumentChunk, RAGQuery, Citation, RAGResponse
from backend.core.logging import logger

class HFHubEmbedder:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_name}"

    def encode(self, texts: List[str]) -> np.ndarray:
        headers = {}
        hf_token = os.environ.get("HF_TOKEN")
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"
        try:
            response = requests.post(
                self.api_url,
                json={"inputs": texts, "options": {"wait_for_model": True}},
                headers=headers,
                timeout=15
            )
            if response.status_code == 200:
                return np.array(response.json())
            else:
                logger.error("hf_embeddings_api_error", status=response.status_code, text=response.text)
        except Exception as e:
            logger.error("hf_embeddings_failed", error=str(e))
        logger.info("using_fallback_dummy_embeddings")
        return np.zeros((len(texts), 384))

class HFHubReranker:
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"

    def predict(self, pairs: List[List[str]]) -> List[float]:
        headers = {}
        hf_token = os.environ.get("HF_TOKEN")
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"
        try:
            payload = {"inputs": [{"text": p[0], "text_pair": p[1]} for p in pairs]}
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=15
            )
            if response.status_code == 200:
                res = response.json()
                if isinstance(res, list):
                    scores = []
                    for item in res:
                        if isinstance(item, dict) and "score" in item:
                            scores.append(item["score"])
                        elif isinstance(item, list) and len(item) > 0 and isinstance(item[0], dict):
                            scores.append(item[0]["score"])
                        else:
                            scores.append(0.5)
                    return scores
        except Exception as e:
            logger.error("hf_reranker_failed", error=str(e))
        scores = []
        for query, text in pairs:
            q_words = set(query.lower().split())
            t_words = set(text.lower().split())
            overlap = len(q_words.intersection(t_words))
            scores.append(float(overlap) / max(len(q_words), 1))
        return scores

# Initialize models lazily
_embedder = None
_reranker = None
_qdrant_client = None
_llm = None

def get_embedder():
    global _embedder
    if _embedder is None:
        if HAS_LOCAL_MODELS:
            try:
                logger.info("loading_embedding_model", model="all-MiniLM-L6-v2")
                _embedder = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                logger.error("local_embedding_loading_failed", error=str(e))
                _embedder = HFHubEmbedder()
        else:
            logger.info("loading_embedding_model_api")
            _embedder = HFHubEmbedder()
    return _embedder

def get_reranker():
    global _reranker
    if _reranker is None:
        if HAS_LOCAL_MODELS:
            try:
                logger.info("loading_cross_encoder", model="cross-encoder/ms-marco-MiniLM-L-6-v2")
                _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            except Exception as e:
                logger.error("local_reranker_loading_failed", error=str(e))
                _reranker = HFHubReranker()
        else:
            logger.info("loading_cross_encoder_api")
            _reranker = HFHubReranker()
    return _reranker

def get_llm():
    global _llm
    if _llm is None:
        # Using OpenRouter to distribute load away from Groq
        _llm = get_openrouter_llm()
    return _llm

def get_qdrant():
    global _qdrant_client
    if _qdrant_client is None:
        url = os.environ.get("QDRANT_URL")
        api_key = os.environ.get("QDRANT_API_KEY")
        if url:
            try:
                _qdrant_client = QdrantClient(url=url, api_key=api_key)
                # Ensure collection exists
                try:
                    _qdrant_client.get_collection("rescuenet_knowledge")
                except Exception:
                    _qdrant_client.create_collection(
                        collection_name="rescuenet_knowledge",
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                    )
                    logger.info("created_qdrant_collection", name="rescuenet_knowledge")
            except Exception as e:
                logger.error("qdrant_init_failed", error=str(e))
                _qdrant_client = None
        else:
            logger.info("QDRANT_URL not set; running in pure-Python BM25 mode.")
            _qdrant_client = None
            
    return _qdrant_client

def sigmoid(x):
    """Convert logits to a 0-1 probability score."""
    return 1 / (1 + math.exp(-x))

def tokenize(text: str) -> List[str]:
    """Simple regex word tokenization for BM25 search."""
    return re.findall(r'\w+', text.lower())

def normalize_query(query: str) -> str:
    """Normalize input query for exact search match caching."""
    return re.sub(r'[^\w\s]', '', query.lower()).strip()

class RAGEvaluator(BaseModel):
    """Schema for the LLM to decide if Qdrant context is sufficient."""
    is_sufficient: Optional[bool] = Field(default=False, description="True if the official context fully answers the user query.")
    response: Optional[str] = Field(default="", description="The synthesized answer if sufficient, OR a targeted web search query if insufficient.")

class RAGEngine:
    def __init__(self):
        self.collection_name = "rescuenet_knowledge"
        self.corpus = []
        self.bm25 = None
        self.cache = {}
        
    def ingest_documents(self, documents: List[Dict[str, Any]]):
        """Expects documents with 'text' and 'metadata'."""
        client = get_qdrant()
        embedder = get_embedder()
        
        # Clear cache when database is updated
        self.cache.clear()
        
        # Append to local corpus ensuring no duplicate text passages
        for doc in documents:
            if not any(d["text"] == doc["text"] for d in self.corpus):
                self.corpus.append(doc)
                
        # Re-initialize the sparse index
        if self.corpus:
            tokenized_corpus = [tokenize(doc["text"]) for doc in self.corpus]
            self.bm25 = BM25Okapi(tokenized_corpus)
            
        if client is not None:
            try:
                texts = [doc["text"] for doc in documents]
                embeddings = embedder.encode(texts).tolist()
                
                points = []
                for idx, (doc, emb) in enumerate(zip(documents, embeddings)):
                    point_id = str(uuid.uuid4())
                    points.append(
                        PointStruct(
                            id=point_id,
                            vector=emb,
                            payload={"text": doc["text"], **doc.get("metadata", {})}
                        )
                    )
                    
                client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info("documents_ingested", count=len(points))
            except Exception as e:
                logger.error("qdrant_upsert_failed_using_bm25_only", error=str(e))
        else:
            logger.info("documents_ingested_bm25_only", count=len(documents))

    def retrieve(self, query_obj: RAGQuery) -> RAGResponse:
        start_time = time.time()
        client = get_qdrant()
        embedder = get_embedder()
        reranker = get_reranker()
        llm = get_llm()
        web_search = DuckDuckGoSearchRun()
        
        # 1. Normalize Query and check cache
        normalized_q = normalize_query(query_obj.query)
        cache_key = (normalized_q, query_obj.disaster_type, query_obj.agency, query_obj.top_k)
        if cache_key in self.cache:
            response = self.cache[cache_key]
            response.processing_time_ms = (time.time() - start_time) * 1000
            return response
            
        # 4. Dense Retrieval
        search_result = []
        if client is not None:
            try:
                # 2. Embed Query
                query_vector = embedder.encode(query_obj.query).tolist()
                
                # 3. Build Metadata Filter
                must_conditions = []
                if query_obj.disaster_type:
                    must_conditions.append(FieldCondition(key="disaster_type", match=MatchValue(value=query_obj.disaster_type)))
                if query_obj.agency:
                    must_conditions.append(FieldCondition(key="agency", match=MatchValue(value=query_obj.agency)))
                    
                query_filter = Filter(must=must_conditions) if must_conditions else None
                
                search_result = client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=query_obj.top_k * 2
                ).points
            except Exception as e:
                logger.error("qdrant_dense_retrieval_failed_using_bm25_only", error=str(e))
        else:
            logger.info("qdrant_bypassed_using_bm25_only")
        
        # 5. Sparse Retrieval (BM25)
        sparse_hits = []
        if self.bm25:
            tokenized_query = tokenize(query_obj.query)
            scores = self.bm25.get_scores(tokenized_query)
            import numpy as np
            top_indices = np.argsort(scores)[::-1][:query_obj.top_k * 2]
            for idx in top_indices:
                if scores[idx] > 0:
                    sparse_hits.append(self.corpus[idx])
                    
        # 6. Merge & Deduplicate
        candidates = []
        seen_texts = set()
        
        # Add dense hits
        for hit in search_result:
            text = hit.payload["text"]
            if text not in seen_texts:
                seen_texts.add(text)
                candidates.append({
                    "id": str(hit.id),
                    "text": text,
                    "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
                })
                
        # Add sparse hits matching the filters
        for doc in sparse_hits:
            doc_meta = doc.get("metadata", {})
            if query_obj.disaster_type and doc_meta.get("disaster_type") != query_obj.disaster_type:
                continue
            if query_obj.agency and doc_meta.get("agency") != query_obj.agency:
                continue
                
            text = doc["text"]
            if text not in seen_texts:
                seen_texts.add(text)
                doc_id = hashlib.md5(text.encode()).hexdigest()
                candidates.append({
                    "id": doc_id,
                    "text": text,
                    "metadata": doc_meta
                })
                
        # 7. Cross Encoder Reranking
        context_parts = []
        citations = []
        avg_confidence = 0.0
        MIN_CONFIDENCE_THRESHOLD = 0.35

        if candidates:
            cross_inp = [[query_obj.query, cand["text"]] for cand in candidates]
            cross_scores = reranker.predict(cross_inp)
            
            scored_cands = []
            for cand, score in zip(candidates, cross_scores):
                scored_cands.append((cand, sigmoid(float(score))))
                
            scored_cands.sort(key=lambda x: x[1], reverse=True)
            
            # Apply confidence thresholding filter
            top_hits = [(cand, score) for cand, score in scored_cands if score >= MIN_CONFIDENCE_THRESHOLD][:query_obj.top_k]
            
            for cand, score in top_hits:
                source = cand["metadata"].get("source", "Unknown Manual")
                citations.append(Citation(
                    source_name=source,
                    chunk_id=cand["id"],
                    relevance_score=score,
                    text_snippet=cand["text"][:100] + "..."
                ))
                context_parts.append(f"[{source}] {cand['text']}")
                avg_confidence += score
                
            if top_hits:
                avg_confidence /= len(top_hits)

        compiled_context = "\n".join(context_parts) if context_parts else "No official SOPs found in Qdrant."

        # 8. Agentic Evaluation & Routing
        route_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an Agentic RAG router for a disaster response system. "
                       "Evaluate if the provided 'Official Context' is sufficient to accurately answer the user's query. "
                       "If YES: Set 'is_sufficient' to true and provide a comprehensive markdown answer based ONLY on the context. "
                       "If NO (or context is empty/irrelevant): Set 'is_sufficient' to false and output a concise, optimized web search query in the 'response' field to find the missing information.\n\n"
                       "You MUST respond with ONLY a valid JSON object (no markdown, no explanation, no function calls). Use this exact schema:\n"
                       '{"is_sufficient": boolean, "response": "string"}'),
            ("human", "User Query: {query}\n\nOfficial Context:\n{context}")
        ])
        
        evaluator_chain = route_prompt | llm
        
        try:
            response = evaluator_chain.invoke({
                "query": query_obj.query,
                "context": compiled_context
            })
            decision = parse_llm_json(response.content, RAGEvaluator)
            
            if decision.is_sufficient:
                # Qdrant successfully answered the query
                final_answer = decision.response
                logger.info("rag_qdrant_hit", query=query_obj.query)
            else:
                # 6. Fallback to Web Search
                logger.info("rag_web_search_triggered", search_query=decision.response)
                web_results = web_search.run(decision.response)
                
                synthesis_prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are a helpful disaster response assistant. Answer the user's query comprehensively using the provided web search results. Use markdown formatting."),
                    ("human", "User Query: {query}\n\nWeb Search Results:\n{web_results}")
                ])
                
                synthesis_chain = synthesis_prompt | llm
                synthesis_result = synthesis_chain.invoke({
                    "query": query_obj.query,
                    "web_results": web_results
                })
                
                final_answer = synthesis_result.content
                avg_confidence = 1.0  # Reset confidence for successful web extraction
                citations = [Citation(
                    source_name="DuckDuckGo Web Search",
                    chunk_id=str(uuid.uuid4()),
                    relevance_score=1.0,
                    text_snippet=web_results[:150] + "..."
                )]
                
        except Exception as e:
            logger.error("rag_agentic_failure", error=str(e))
            # Resilient direct-context fallback if Groq/LLM service is offline or dummy
            if context_parts:
                final_answer = f"Based on retrieved guidelines:\n" + "\n".join(context_parts)
            else:
                final_answer = "No authoritative guidelines found for this query."

        response = RAGResponse(
            answer=final_answer,
            citations=citations,
            confidence_score=avg_confidence,
            processing_time_ms=(time.time() - start_time) * 1000
        )
        
        self.cache[cache_key] = response
        return response

rag_engine = RAGEngine()
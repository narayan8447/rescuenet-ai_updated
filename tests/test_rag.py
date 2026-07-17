import pytest
import time
from backend.rag.models import RAGQuery
from backend.rag.rag_engine import rag_engine

@pytest.fixture(scope="module", autouse=True)
def setup_rag():
    # Ingest some test documents
    docs = [
        {"text": "During a flood, evacuate all patients from the ground floor to higher levels.", "metadata": {"disaster_type": "flood", "source": "NDMA_Flood_SOP"}},
        {"text": "For earthquake response, ensure power is cut to prevent fires.", "metadata": {"disaster_type": "earthquake", "source": "NDRF_Earthquake_SOP"}},
        {"text": "Hospitals should maintain a 3-day backup of medical oxygen.", "metadata": {"agency": "WHO", "source": "Hospital_Guidelines"}}
    ]
    rag_engine.ingest_documents(docs)

def test_rag_retrieval_flood():
    query = RAGQuery(query="What should we do with patients during a flood?", top_k=2)
    response = rag_engine.retrieve(query)
    
    assert response.confidence_score > 0
    assert len(response.citations) > 0
    
    # Check if the correct document was retrieved based on dense/cross-encoder matching
    assert any("ground floor" in cit.text_snippet for cit in response.citations)

def test_rag_metadata_filtering():
    query = RAGQuery(query="What should we do for earthquake response?", disaster_type="earthquake", top_k=1)
    response = rag_engine.retrieve(query)
    
    assert len(response.citations) > 0
    assert "power is cut" in response.citations[0].text_snippet

def test_rag_hybrid_search_bm25():
    # Ingest a specific keyword-heavy document
    docs = [
        {"text": "Protocol ALPHA-99: Evacuate all personnel using designated route Blue.", "metadata": {"disaster_type": "wildfire", "source": "NFPA_Alpha_Protocol"}}
    ]
    rag_engine.ingest_documents(docs)
    
    # Query with exact keyword ALPHA-99
    query = RAGQuery(query="ALPHA-99", top_k=1)
    response = rag_engine.retrieve(query)
    
    assert len(response.citations) > 0
    assert "ALPHA-99" in response.citations[0].text_snippet

def test_rag_threshold_filtering():
    # Query for completely irrelevant random text
    query = RAGQuery(query="rainbows and butterflies dancing in the sky", top_k=1)
    response = rag_engine.retrieve(query)
    
    # Due to thresholding, it should return no citations and fallback message
    assert len(response.citations) == 0
    assert "No authoritative guidelines found" in response.answer

def test_rag_query_caching():
    query = RAGQuery(query="Evacuate ground floor levels.", top_k=1)
    
    # First search (populates cache)
    t1_start = time.time()
    resp1 = rag_engine.retrieve(query)
    t1_duration = time.time() - t1_start
    
    # Second search (cache hit)
    t2_start = time.time()
    resp2 = rag_engine.retrieve(query)
    t2_duration = time.time() - t2_start
    
    assert resp1.answer == resp2.answer
    assert t2_duration < t1_duration


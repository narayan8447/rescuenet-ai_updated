"""
LLM Pool - Distributes LLM calls across multiple providers to maximize
throughput and avoid rate limits on any single provider's free tier.

Provider Strategy:
  - Groq:       llama-3.1-8b-instant  (6,000 TPM free tier)
  - OpenRouter:  google/gemma-2-9b-it:free  (separate rate limit pool)

Agents are split roughly 50/50 across providers so that no single
provider's TPM budget is exhausted during a pipeline run.
"""
import os
import json
import re
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


def parse_llm_json(response_content: str, schema_class):
    """Parse raw LLM text response as JSON and validate with a Pydantic schema.
    
    This bypasses the broken with_structured_output() / function-calling pathway
    in langchain-google-genai which causes 'tool_use_failed' errors with Gemini models.
    Instead, we ask the LLM to output plain JSON and parse it manually.
    """
    text = response_content.strip()
    # Remove markdown code fences (```json ... ``` or ``` ... ```)
    fence_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    # Extract the outermost JSON object
    obj_match = re.search(r'\{.*\}', text, re.DOTALL)
    if obj_match:
        text = obj_match.group(0)
    data = json.loads(text)
    return schema_class(**data)


def get_google_llm(max_retries: int = 10):
    """Fallback: Redirects Google LLM traffic to Groq to bypass Gemini quota limits."""
    # The user has a valid GROQ_API_KEY with higher rate limits (30 RPM).
    return get_groq_llm(max_retries)


def get_groq_llm(max_retries: int = 10) -> ChatGroq:
    """Return a Groq-backed LLM (llama-3.1-8b-instant)."""
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.environ.get("GROQ_API_KEY", "dummy_key"),
        max_retries=max_retries,
    )


def get_openrouter_llm(max_retries: int = 10):
    """Fallback: Redirects OpenRouter LLM traffic to Groq to bypass upstream rate limits."""
    # OpenRouter's free models are throwing 429 upstream errors. 
    # The user has a valid GROQ_API_KEY with reliable limits.
    return get_groq_llm(max_retries)

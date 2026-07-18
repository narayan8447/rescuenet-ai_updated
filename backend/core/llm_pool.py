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
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


def get_google_llm(max_retries: int = 10) -> ChatGoogleGenerativeAI:
    """Return a Google-backed LLM (gemini-2.5-flash)."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=os.environ.get("GOOGLE_API_KEY", "dummy_key"),
        max_retries=max_retries,
    )


def get_groq_llm(max_retries: int = 10) -> ChatGroq:
    """Return a Groq-backed LLM (llama-3.1-8b-instant)."""
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.environ.get("GROQ_API_KEY", "dummy_key"),
        max_retries=max_retries,
    )


def get_openrouter_llm(max_retries: int = 10) -> ChatOpenAI:
    """Return an OpenRouter-backed LLM (google/gemma-2-9b-it:free).
    
    OpenRouter exposes an OpenAI-compatible API, so we use ChatOpenAI
    with a custom base_url.  The model has tool-calling support and
    a generous free-tier rate limit.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "dummy_key")
    return ChatOpenAI(
        model="google/gemma-4-31b-it:free",
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        max_retries=max_retries,
        extra_body={
            "models": [
                "google/gemma-4-31b-it:free",
                "qwen/qwen3-next-80b-a3b-instruct:free",
                "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
            ]
        },
        default_headers={
            "HTTP-Referer": "https://rescuenet-ai.onrender.com",
            "X-Title": "RescueNet AI",
        },
    )

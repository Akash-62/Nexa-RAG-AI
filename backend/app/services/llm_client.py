"""
Provider-agnostic LLM factory. Switch provider via LLM_PROVIDER env var.
Never import provider SDKs directly outside this module.
"""
from app.core.config import settings


def get_llm(temperature: float = 0.0):
    match settings.llm_provider:
        case "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.openai_api_key,
                temperature=temperature,
            )
        case "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=settings.llm_model,
                api_key=settings.anthropic_api_key,
                temperature=temperature,
            )
        case "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=settings.llm_model,
                google_api_key=settings.google_api_key,
                temperature=temperature,
            )
        case "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=settings.llm_model,
                api_key=settings.groq_api_key,
                temperature=temperature,
            )
        case _:
            raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}. Choose openai | anthropic | gemini | groq")

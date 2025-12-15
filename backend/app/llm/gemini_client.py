import os
import json
from google import genai
from google.genai.types import GenerateContentConfig
from app.services.cache_service import cache_service


class GeminiClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY environment variable")

        self.client = genai.Client(api_key=api_key)
        self.model = "models/gemini-2.5-flash"
        self.embed_model = "models/text-embedding-004"

    def classify_document(self, text: str) -> dict:
        """
        Classify document with intelligent caching.
        Checks cache first, only calls API if needed.
        """

        # ✅ CHECK CACHE FIRST
        cached = cache_service.get(text, "classify")
        if cached:
            return cached

        # ❌ CACHE MISS - Call Gemini API
        prompt = f"""
        Classify this document into:
        - invoice
        - receipt
        - purchase_order
        - resume
        - report
        - unknown

        Respond ONLY in JSON including:
        {{
            "document_type": "...",
            "confidence": 0.xx
        }}

        TEXT:
        {text}
        """

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            result = json.loads(response.text)

            # ✅ SAVE TO CACHE
            cache_service.set(text, "classify", result)

            return result

        except Exception as e:
            print(f"⚠️ Gemini API error: {e}")
            return {"document_type": "unknown", "confidence": 0.0}

    def summarize(self, text: str) -> str:
        """
        Summarize text with caching support.
        """

        # ✅ CHECK CACHE FIRST
        cached = cache_service.get(text, "summarize")
        if cached:
            return cached.get("summary", "")

        # ❌ CACHE MISS - Call API
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[f"Summarize this document concisely:\n{text}"]
            )

            summary = response.text

            # ✅ SAVE TO CACHE
            cache_service.set(text, "summarize", {"summary": summary})

            return summary

        except Exception as e:
            print(f"⚠️ Gemini API error: {e}")
            return "Summary unavailable"

    def generate_embeddings(self, text: str):
        """
        Generate embeddings with caching.
        """

        # ✅ CHECK CACHE FIRST
        cached = cache_service.get(text, "embeddings")
        if cached:
            return cached.get("values", [])

        # ❌ CACHE MISS - Call API
        try:
            resp = self.client.models.embed_content(
                model=self.embed_model,
                contents=[text]
            )

            values = resp.embeddings[0].values

            # ✅ SAVE TO CACHE
            cache_service.set(text, "embeddings", {"values": values})

            return values

        except Exception as e:
            print(f"⚠️ Gemini API error: {e}")
            return []

    def extract_structured(self, text: str, doc_type: str):
        """
        Extract structured data with caching.
        Cache key includes both text AND doc_type.
        """

        # Create composite cache key
        cache_text = f"{doc_type}|{text}"

        # ✅ CHECK CACHE FIRST
        cached = cache_service.get(cache_text, "extract")
        if cached:
            return cached

        # ❌ CACHE MISS - Call API
        prompt = f"""
Extract structured fields from this {doc_type} document.
Return ONLY valid JSON. No explanations.

Document:
{text}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            result = json.loads(response.text)

            # ✅ SAVE TO CACHE
            cache_service.set(cache_text, "extract", result)

            return result

        except Exception as e:
            print(f"⚠️ Gemini API error: {e}")
            return {"raw_text": text}


gemini = GeminiClient()
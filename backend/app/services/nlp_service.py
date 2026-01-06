from app.llm.gemini_client import GeminiClient

class NLPService:
    def __init__(self):
        self.gemini = GeminiClient()

    def summarize(self, text: str) -> str:
        return self.gemini.summarize(text)

    def embed_text(self, text: str):
        return self.gemini.generate_embeddings(text)

nlp_service = NLPService()

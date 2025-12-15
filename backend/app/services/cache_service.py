import hashlib
import json
import os
from typing import Optional
from datetime import datetime


class CacheService:
    """
    Smart caching layer for Gemini API responses.
    Reduces API calls by 50-90% by caching OCR text and LLM results.
    """

    def __init__(self):
        self.cache_dir = "cache/gemini"
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_key(self, text: str, operation: str) -> str:
        """
        Generate unique cache key from text content + operation type.
        Uses MD5 hash to handle long texts.
        """
        # Normalize text to avoid cache misses from whitespace differences
        normalized = " ".join(text.split())
        content = f"{operation}:{normalized}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get(self, text: str, operation: str) -> Optional[dict]:
        """
        Retrieve cached result if it exists.

        Args:
            text: The document text (OCR output)
            operation: Type of operation ('classify', 'extract', 'summarize')

        Returns:
            Cached result dict or None if not found
        """
        key = self._get_cache_key(text, operation)
        path = os.path.join(self.cache_dir, f"{key}.json")

        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"✅ CACHE HIT [{operation}] - Saved 1 API call! (key: {key[:8]}...)")
                    return data.get("result")
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ Cache read error: {e}")
                return None

        print(f"❌ CACHE MISS [{operation}] - Will call Gemini API")
        return None

    def set(self, text: str, operation: str, result: dict):
        """
        Save result to cache with metadata.

        Args:
            text: The document text
            operation: Type of operation
            result: The API response to cache
        """
        key = self._get_cache_key(text, operation)
        path = os.path.join(self.cache_dir, f"{key}.json")

        cache_data = {
            "operation": operation,
            "cached_at": datetime.now().isoformat(),
            "text_length": len(text),
            "result": result
        }

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
            print(f"💾 CACHED [{operation}] (key: {key[:8]}...)")
        except IOError as e:
            print(f"⚠️ Cache write error: {e}")

    def clear(self, operation: Optional[str] = None):
        """
        Clear cache files.

        Args:
            operation: If specified, only clear caches for this operation type
        """
        if not os.path.exists(self.cache_dir):
            return

        deleted = 0
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.json'):
                continue

            filepath = os.path.join(self.cache_dir, filename)

            if operation:
                # Only delete if operation matches
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        if data.get("operation") == operation:
                            os.remove(filepath)
                            deleted += 1
                except:
                    continue
            else:
                # Delete all
                os.remove(filepath)
                deleted += 1

        print(f"🗑️ Cleared {deleted} cache entries")

    def stats(self) -> dict:
        """Get cache statistics."""
        if not os.path.exists(self.cache_dir):
            return {"total_entries": 0}

        files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]

        ops = {}
        total_size = 0

        for filename in files:
            filepath = os.path.join(self.cache_dir, filename)
            try:
                total_size += os.path.getsize(filepath)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    op = data.get("operation", "unknown")
                    ops[op] = ops.get(op, 0) + 1
            except:
                continue

        return {
            "total_entries": len(files),
            "total_size_kb": round(total_size / 1024, 2),
            "by_operation": ops
        }


# Singleton instance
cache_service = CacheService()
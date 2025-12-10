"""
Translation Service using Lingva Translate API.

Lingva is a free, open-source translation service that acts as an alternative
front-end for Google Translate without tracking.
"""

import aiohttp
import asyncio
import logging
from typing import Optional, Dict, List
from app.core.config import settings

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Service for translating messages using Lingva Translate API.

    Lingva Translate is a privacy-focused translation service.
    Multiple instances available for reliability.
    """

    def __init__(self):
        # List of Lingva instances (fallback if one is down)
        self.lingva_instances = [
            "https://lingva.thedaviddelta.com/api/v1",  # Primary
            "https://translate.plausibility.cloud/api/v1",  # Alternative 1
            "https://lingva.ml/api/v1",  # Alternative 2 (original, but sometimes down)
        ]
        self.current_instance_index = 0
        self.base_url = self.lingva_instances[self.current_instance_index]
        self.timeout = aiohttp.ClientTimeout(total=3)  # Fast timeout for quick response
        self._session = None  # Shared session for better performance

    async def _get_session(self):
        """Get or create shared aiohttp session for better performance."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def translate(
        self, text: str, source_lang: str = "auto", target_lang: str = "en"
    ) -> Dict[str, str]:
        """
        Translate text from source language to target language.
        Tries multiple Lingva instances for reliability.

        Args:
            text: Text to translate
            source_lang: Source language code (use 'auto' for auto-detection)
            target_lang: Target language code

        Returns:
            Dictionary with translation and detected source language
            {
                "translation": "translated text",
                "source_lang": "detected language code"
            }
        """
        if not text or not text.strip():
            return {"translation": text, "source_lang": source_lang}

        # If source and target are same, no translation needed
        if source_lang == target_lang and source_lang != "auto":
            return {"translation": text, "source_lang": source_lang}

        # Try each Lingva instance until one works
        for attempt, instance_url in enumerate(self.lingva_instances):
            try:
                # URL encode the text for the API request
                from urllib.parse import quote

                encoded_text = quote(text)

                # Lingva API endpoint format: /api/v1/{source}/{target}/{query}
                url = f"{instance_url}/{source_lang}/{target_lang}/{encoded_text}"

                session = await self._get_session()
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Lingva API response format:
                        # {
                        #   "translation": "translated text",
                        #   "info": {
                        #     "detectedSource": "en",
                        #     ...
                        #   }
                        # }

                        translation = data.get("translation", text)
                        detected_lang = source_lang

                        if "info" in data and "detectedSource" in data["info"]:
                            detected_lang = data["info"]["detectedSource"]

                        # Update base_url to this working instance
                        self.base_url = instance_url
                        return {
                            "translation": translation,
                            "source_lang": detected_lang,
                        }
                    else:
                        # Try next instance
                        continue

            except asyncio.TimeoutError:
                logger.warning(f"⏱️ Timeout with instance: {instance_url}")
                continue
            except Exception as e:
                logger.warning(f"❌ Error with instance {instance_url}: {str(e)}")
                continue

        # All instances failed, return original text
        logger.error("❌ All Lingva instances failed! Returning original text.")
        return {"translation": text, "source_lang": source_lang}

    async def translate_batch(
        self, texts: List[str], source_lang: str = "auto", target_lang: str = "en"
    ) -> List[Dict[str, str]]:
        """
        Translate multiple texts at once.

        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            List of translation results
        """
        import asyncio

        tasks = [self.translate(text, source_lang, target_lang) for text in texts]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch translation error for text {i}: {result}")
                processed_results.append(
                    {"translation": texts[i], "source_lang": source_lang}
                )
            else:
                processed_results.append(result)

        return processed_results

    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get list of supported language codes.

        Returns:
            Dictionary of language codes to language names
        """
        return {
            "auto": "Auto Detect",
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese (Simplified)",
            "zh-TW": "Chinese (Traditional)",
            "ar": "Arabic",
            "hi": "Hindi",
            "bn": "Bengali",
            "ur": "Urdu",
            "tr": "Turkish",
            "nl": "Dutch",
            "pl": "Polish",
            "sv": "Swedish",
            "da": "Danish",
            "fi": "Finnish",
            "no": "Norwegian",
            "cs": "Czech",
            "el": "Greek",
            "he": "Hebrew",
            "th": "Thai",
            "vi": "Vietnamese",
            "id": "Indonesian",
            "ms": "Malay",
            "fil": "Filipino",
            "uk": "Ukrainian",
            "ro": "Romanian",
            "hu": "Hungarian",
            "sk": "Slovak",
            "bg": "Bulgarian",
            "hr": "Croatian",
            "sr": "Serbian",
            "lt": "Lithuanian",
            "lv": "Latvian",
            "et": "Estonian",
            "sl": "Slovenian",
            "fa": "Persian",
            "sw": "Swahili",
            "af": "Afrikaans",
        }


# Global translation service instance
translation_service = TranslationService()

"""
Local LLM integration for code summarization.
Supports ollama and fallback to basic analysis.
"""

import re
import time
from typing import Dict, Any, Optional, List
from loguru import logger

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests library not available, LLM summarization disabled")

from .config import LLM_CONFIG, PROMPT_TEMPLATES, RESPONSE_PATTERNS


class LocalLLMClient:
    """
    Client for interacting with local LLM backends.
    Currently supports ollama.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize LLM client.

        Args:
            config: Optional configuration overrides
        """
        self.config = {**LLM_CONFIG, **(config or {})}
        self.backend = self.config["backend"]
        self.available = False

        if self.backend == "none":
            logger.info("LLM backend disabled (backend='none')")
            return

        if not REQUESTS_AVAILABLE:
            logger.warning("requests library not available, LLM client unavailable")
            return

        # Test connection
        if self.backend == "ollama":
            self.available = self._test_ollama_connection()
        else:
            logger.warning(f"Unsupported LLM backend: {self.backend}")

    def _test_ollama_connection(self) -> bool:
        """Test if ollama is running and accessible."""
        try:
            response = requests.get(
                f"{self.config['api_base']}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                logger.info("Ollama connection successful")
                return True
            else:
                logger.warning(f"Ollama responded with status {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    def generate(self, prompt: str) -> Optional[str]:
        """
        Generate text from prompt using configured LLM.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Generated text or None if unavailable
        """
        if not self.available:
            logger.debug("LLM not available, returning None")
            return None

        if self.backend == "ollama":
            return self._generate_ollama(prompt)

        return None

    def _generate_ollama(self, prompt: str) -> Optional[str]:
        """Generate using ollama backend."""
        try:
            url = f"{self.config['api_base']}/api/generate"
            payload = {
                "model": self.config["model"],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config["temperature"],
                    "num_predict": self.config["max_tokens"]
                }
            }

            logger.debug(f"Sending request to ollama: {self.config['model']}")
            start_time = time.time()

            response = requests.post(
                url,
                json=payload,
                timeout=self.config["timeout"]
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("response", "")
                logger.info(f"LLM generation completed in {elapsed:.2f}s")
                return generated_text
            else:
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error("LLM request timed out")
            return None
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None

    def is_available(self) -> bool:
        """Check if LLM is available."""
        return self.available


class SummaryParser:
    """
    Parses LLM responses into structured summaries.
    """

    @staticmethod
    def parse_summary_response(response: str) -> Dict[str, Any]:
        """
        Parse a summary response into structured data.

        Args:
            response: Raw LLM response text

        Returns:
            Dict with parsed fields: purpose, key_points, dependencies, complexity
        """
        parsed = {
            "purpose": "",
            "key_points": [],
            "dependencies": [],
            "complexity": None
        }

        # Extract purpose
        purpose_match = re.search(RESPONSE_PATTERNS["purpose"], response, re.DOTALL | re.MULTILINE)
        if purpose_match:
            parsed["purpose"] = purpose_match.group(1).strip()

        # Extract key points
        key_points_match = re.search(RESPONSE_PATTERNS["key_points"], response, re.MULTILINE)
        if key_points_match:
            points_text = key_points_match.group(1)
            # Split by bullet points
            points = re.findall(r'[-•]\s*(.+)', points_text)
            parsed["key_points"] = [p.strip() for p in points]

        # Extract dependencies
        deps_match = re.search(RESPONSE_PATTERNS["dependencies"], response, re.MULTILINE)
        if deps_match:
            deps_text = deps_match.group(1).strip()
            # Split by commas
            parsed["dependencies"] = [d.strip() for d in deps_text.split(",") if d.strip()]

        # Extract complexity
        complexity_match = re.search(RESPONSE_PATTERNS["complexity"], response)
        if complexity_match:
            try:
                parsed["complexity"] = int(complexity_match.group(1))
            except ValueError:
                pass

        return parsed

    @staticmethod
    def format_prompt(
        template_type: str,
        **kwargs
    ) -> str:
        """
        Format a prompt using a template.

        Args:
            template_type: Type of template ("file", "symbol", "architecture", "layer")
            **kwargs: Template variables

        Returns:
            Formatted prompt string
        """
        template = PROMPT_TEMPLATES.get(template_type, PROMPT_TEMPLATES["file"])
        return template.format(**kwargs)

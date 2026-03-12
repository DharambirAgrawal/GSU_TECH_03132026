# app/utils/llm_clients.py
# -----------------------------------------
# Wrappers for calling OpenAI, Anthropic, and Google Gemini APIs.
# All LLM calls in Vigil go through these wrappers so API keys,
# retry logic, and error handling are in one place.
#
# IMPORTS NEEDED:
#   import openai                                       # OpenAI SDK (pip install openai)
#   import anthropic                                    # Anthropic SDK (pip install anthropic)
#   import httpx                                        # For Perplexity API (REST API, no SDK)
#   import os                                           # Read API keys from env vars
#   import time                                         # For retry backoff sleep
#   import logging
#
# ENVIRONMENT VARIABLES REQUIRED (set in .env):
#   OPENAI_API_KEY      — for ChatGPT (gpt-4o)
#   ANTHROPIC_API_KEY   — for Claude (claude-3-5-sonnet)
#   PERPLEXITY_API_KEY  — for Perplexity (sonar-pro)
#   GOOGLE_API_KEY      — for Gemini (gemini-1.5-pro)
#
# -----------------------------------------------------------
# FUNCTION: get_chatgpt_response(query: str, temperature: float = 0.3) -> str
# -----------------------------------------------------------
# PURPOSE:
#   Sends a query to OpenAI GPT-4o and returns the response text.
#
# IMPLEMENTATION:
#   1. Initialize openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
#   2. Call client.chat.completions.create() with:
#         model = "gpt-4o"
#         messages = [
#           { "role": "system", "content": "You are a helpful assistant." },
#           { "role": "user", "content": query }
#         ]
#         temperature = temperature
#         max_tokens = 1000
#   3. Return response.choices[0].message.content
#   4. On openai.RateLimitError: raise RateLimitError (caller handles retry)
#   5. On any other exception: raise LLMClientError with platform="chatgpt"
#
# -----------------------------------------------------------
# FUNCTION: get_claude_response(query: str, temperature: float = 0.3) -> str
# -----------------------------------------------------------
# PURPOSE:
#   Sends a query to Anthropic Claude (claude-3-5-sonnet-20241022).
#
# IMPLEMENTATION:
#   1. Initialize anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
#   2. Call client.messages.create() with:
#         model = "claude-3-5-sonnet-20241022"
#         max_tokens = 1000
#         messages = [{ "role": "user", "content": query }]
#   3. Return response.content[0].text
#   4. On anthropic.RateLimitError: raise RateLimitError
#
# -----------------------------------------------------------
# FUNCTION: get_perplexity_response(query: str) -> str
# -----------------------------------------------------------
# PURPOSE:
#   Sends a query to Perplexity AI via their REST API.
#   Perplexity is important because it's a search-augmented AI
#   that is particularly influential in consumer queries.
#
# IMPLEMENTATION:
#   Uses httpx to POST to https://api.perplexity.ai/chat/completions
#   Headers: { "Authorization": f"Bearer {PERPLEXITY_API_KEY}" }
#   Body: { "model": "sonar-pro", "messages": [...] }
#   Parse JSON response and return message content string
#
# -----------------------------------------------------------
# FUNCTION: get_gemini_response(query: str) -> str
# -----------------------------------------------------------
# PURPOSE:
#   Sends a query to Google Gemini 1.5 Pro via the google-generativeai SDK.
#
# IMPORTS (inside function to keep optional):
#   import google.generativeai as genai
#
# IMPLEMENTATION:
#   1. genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
#   2. model = genai.GenerativeModel("gemini-1.5-pro")
#   3. response = model.generate_content(query)
#   4. Return response.text
#
# -----------------------------------------------------------
# CUSTOM EXCEPTIONS:
#
#   class RateLimitError(Exception):
#       """Raised when any LLM API returns a rate limit error."""
#       def __init__(self, platform: str):
#           self.platform = platform
#           super().__init__(f"Rate limit hit on {platform}")
#
#   class LLMClientError(Exception):
#       """Raised for non-rate-limit errors from any LLM client."""
#       def __init__(self, platform: str, original_error: Exception):
#           self.platform = platform
#           self.original_error = original_error
#           super().__init__(f"LLM error on {platform}: {str(original_error)}")

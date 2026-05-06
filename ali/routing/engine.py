# TODO: Ali — multi-model routing engine. The core of the AI intelligence layer.
# route_request(task_type: str, context: dict) → LLMResponse
#   1. Classify request complexity via classifier.py
#   2. Select model tier: SMALL | LARGE | VALIDATOR
#   3. Pick best available model within that tier (cost + latency aware)
#   4. Dispatch to the appropriate client in clients/
#
# Model tier mapping:
#   SMALL  → GPT-4o mini, Llama 3.1 8B, Mistral 7B
#   LARGE  → GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro
#   VALIDATOR → GPT-4o (critic mode), Claude 3.5 Sonnet
#
# Task types that map to SMALL:
#   "chat_topics", "short_explanation", "persona_label",
#   "preference_parse", "quick_edit", "notification_message"
#
# Task types that map to LARGE:
#   "itinerary_generation", "complex_refinement",
#   "conflict_resolution", "rag_explanation", "what_if"
#
# Task types that map to VALIDATOR:
#   "validate_itinerary", "critic_check"

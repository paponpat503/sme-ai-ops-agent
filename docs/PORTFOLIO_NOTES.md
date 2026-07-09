# Portfolio Notes

## One-line pitch

I built an SME AI Ops Agent that combines RAG, structured JSON outputs, tool-calling architecture, CRM risk detection, and evaluation harnesses for B2B workflow automation.

## What to show in interview

1. `/agent/ask` returns validated Pydantic output.
2. CRM tools are separated from agent logic.
3. RAG search is separate from answer generation.
4. Evaluation cases measure intent, inclusion/exclusion, and action correctness.
5. Fallback logic exists even without an LLM API.
6. The architecture can be upgraded to OpenAI, Claude, Gemini, MCP, n8n, or a real CRM API.

## What to say

Most chatbot demos are not production systems. I designed this around controlled tools, structured outputs, validation, retrieval, evidence, fallbacks, and evaluation.

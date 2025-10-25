# API Gateway Placeholder

This folder is reserved for an optional Edge/API gateway service (e.g., FastAPI + rate limiting, or an Envoy/NGINX configuration generator).

For now it contains no code so the intent is explicit and does not mislead contributors.

When you are ready to proceed, consider:
1. Defining routing/authn requirements that are not already fulfilled by `backend/api`.
2. Choosing an implementation (FastAPI, Express, or infrastructure-managed gateway).
3. Adding integration tests that cover edge cases (rate limits, request signing, etc.).

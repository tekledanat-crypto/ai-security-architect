# ADR-0001: AI Provider Abstraction (Azure OpenAI primary)

**Status:** Accepted · **Chunk:** 1

## Context
Target provider is Azure OpenAI (portfolio fit), but the developer's Azure
subscription is unconfirmed. The build must not be blocked on Azure access.

## Decision
One internal interface `AIProvider` (chat_stream, tool-calls, token accounting)
with two implementations selected by `AI_PROVIDER` env var:
- `azure-openai` — Azure OpenAI via the `openai` SDK's AzureOpenAI client.
  API key locally; Managed Identity + Key Vault in Azure deployment.
- `openai` — plain OpenAI as a drop-in local fallback.

## Consequences
+ Unblocked local dev; provider swap is config, not code.
+ Demonstrates clean architecture / dependency inversion.
- Must avoid Azure-only API features or gate them behind capability flags.

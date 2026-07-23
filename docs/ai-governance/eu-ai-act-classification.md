# EU AI Act — Risk Classification Memo

**System:** AI Security Architect Assistant · **Version:** 0.9.0
**Regulation:** Regulation (EU) 2024/1689 (AI Act)
**Conclusion: Limited risk — transparency obligations apply (Article 50).**

> This is an engineering classification memo, not legal advice. A real deployment
> would have this reviewed by counsel. It is included because classifying an AI system
> honestly is part of building one responsibly — and because the temptation to
> overclaim a "high-risk" tier to look impressive is exactly the wrong instinct.

---

## 1. Is it an AI system? — Yes

The system uses a generative model (Azure OpenAI) to infer questions, narrate results,
and produce architecture proposals from natural-language input. It meets the Article
3(1) definition.

**Scope note:** the *scoring engine* is deterministic rule evaluation, not machine
learning. Only the conversational layer is in scope for the Act.

## 2. Is it a prohibited practice? — No (Article 5)

No subliminal manipulation, no exploitation of vulnerabilities, no social scoring, no
biometric categorisation, no emotion inference, no real-time remote biometric
identification. The system evaluates cloud infrastructure configurations, not people.

## 3. Is it high-risk? — No

**Annex I (product safety components):** not applicable. This is not a safety component
of a regulated product.

**Annex III (listed high-risk areas)** — assessed point by point:

| Annex III area | Applies? | Why |
|---|---|---|
| 1. Biometrics | No | No biometric processing |
| 2. Critical infrastructure | **No — see below** | Nearest candidate; analysed in detail |
| 3. Education/vocational training | No | Not used for access or assessment of learners |
| 4. Employment/worker management | No | No decisions about people |
| 5. Essential services & benefits | No | No eligibility decisions; no creditworthiness |
| 6. Law enforcement | No | Not used by or for law enforcement |
| 7. Migration/asylum/border | No | Not applicable |
| 8. Justice & democratic processes | No | Not applicable |

**On Annex III(2) — critical infrastructure.** This is the point deserving genuine
scrutiny, so it gets it. Annex III(2) covers AI intended as a *safety component in the
management and operation* of critical digital infrastructure. This system is not:

- It is an **advisory design-time tool**, not an operational component. It does not run
  in, manage, or control any production system.
- It has **no actuation capability**. Its tools are read-only analysis functions over a
  static corpus (`docs/ai-governance/owasp-llm-top10-self-assessment.md`, LLM06). It
  cannot deploy, modify, or disable infrastructure.
- Its output is **advice to a qualified human**, who designs and deploys separately.
  The system prompt and every report state that final decisions require human review.
- **Failure mode is bounded:** bad advice may lead a practitioner toward a weaker
  design, but cannot itself cause an outage or breach. It sits alongside a threat
  model or a checklist, not alongside a control plane.

**If that changed** — if the system gained the ability to apply changes to live
infrastructure — this classification would need to be redone. That is a design
boundary, and it is deliberate.

## 4. GPAI obligations? — No (Chapter V)

The system is a *downstream deployer* of a general-purpose model, not a provider of
one. It does not train, fine-tune, or place a GPAI model on the market. Obligations
under Articles 53–55 fall on the model provider (Microsoft/OpenAI).

## 5. Limited risk → transparency obligations (Article 50)

The system interacts directly with humans, so Article 50(1) applies: users must be
informed they are interacting with an AI system.

### How each obligation is met

| Obligation | Implementation | Location |
|---|---|---|
| **50(1)** — Inform users they are interacting with AI | The interface is explicitly "AI Assistant" with an AI-badged agent; the assistant introduces itself as "your AI Security Architect" | `frontend/src/components/chat-panel.tsx`, `backend/app/ai/prompts.py` |
| **50(1)** — Disclosure is clear and not buried | Persistent footer under the composer, visible on every turn: *"Findings are produced by a deterministic engine over 137 controls — the assistant narrates, it doesn't invent."* | `chat-panel.tsx` |
| Beyond the minimum — capability honesty | The tool-activity rail shows users *live* which tools produced which claims, rather than presenting all output as model knowledge | `frontend/src/components/tool-activity.tsx` |
| Beyond the minimum — provenance in artefacts | Every exported report carries a Methodology & Scope section stating how findings are produced and that the assessment reviews declared design, not a running deployment | `backend/app/reports/template.py` |

**50(2) (synthetic content marking):** the system generates text and diagrams, not
audio/image/video deepfakes. Machine-readable marking of synthetic media is not
applicable. Reports are nonetheless attributed to the tool and timestamped.

**50(4) (deepfakes / public-interest text):** not applicable — no such content is
generated.

## 6. Conclusion

**Limited risk.** Transparency obligations under Article 50 apply and are met, with
several measures going beyond the minimum (live tool provenance, methodology disclosure
in artefacts). No high-risk obligations (conformity assessment, CE marking, registration,
post-market monitoring) are triggered.

**Reclassification triggers** — any of these would require redoing this memo:
1. Gaining the ability to apply changes to live infrastructure (→ re-examine Annex III(2))
2. Being marketed as an authoritative compliance certification rather than advisory
3. Processing personal data or making determinations about individuals
4. Training or fine-tuning a model placed on the market (→ Chapter V)

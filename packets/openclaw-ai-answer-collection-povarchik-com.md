# OpenClaw AI Answer Collection Packet

## Audit target

- Run ID: povarchik-com-20260822-0313
- Entity: **Pablo Povarchik**
- Primary domain: **povarchik.com**
- Generated at: 2026-08-22T03:13:00-04:00

## Providers

Run every question against these providers, in this order:

1. ChatGPT
2. Claude
3. Gemini

Use each provider's normal consumer web interface.

Do not use APIs.

---

# Agent instructions

This is an evidence-collection task only.

Your job is to ask the supplied questions and record exactly what the providers return.

Do not analyze, summarize, compare, correct, score, or interpret the answers.

## Temporary/private mode

For every provider, use its temporary/private conversation mode when available.

Examples include:

- ChatGPT — Temporary Chat
- Claude — Incognito chat
- Gemini — Temporary Chat

Use the provider's own temporary/private mode rather than a normal saved conversation.

If no such mode is available, use a fresh normal conversation and record:

`Temporary/private mode: Not available`

Do not change this behavior between questions for the same provider.

The purpose is to minimize contamination from:

- conversation history;
- account memory;
- personalization;
- previous chats;
- Projects;
- custom assistants;
- uploaded files.

Do not deliberately provide the provider with prior knowledge about the audited entity.

---

# Collection protocol

For every provider/question pair:

1. Start a new temporary/private conversation.
2. Ask the **Rendered question exactly as written**.
3. Do not add:
   - instructions;
   - context;
   - the company URL;
   - aliases;
   - requests for citations;
   - requests to search the web.
4. Do not visit or research the audited entity before asking the question.
5. Do not manually enable or disable:
   - web search;
   - browsing;
   - deep research;
   - reasoning modes;
   - special tools.
6. Submit the question once.
7. Wait until the provider has finished answering.
8. Do not regenerate the answer.
9. Do not ask follow-up questions.
10. Record the complete answer as faithfully as possible.
11. Preserve wording, paragraphs, headings, lists, tables, citation markers, links, and caveats.
12. Capture only citations and sources actually exposed by the provider.
13. A provider's Sources/Citations panel may be opened to capture source information already exposed for that answer.
14. Do not search separately for sources, infer sources, or ask the provider what sources it used.
15. Continue to the next attempt if a provider fails.
16. Create a response record for every required provider/question pair, including failed attempts.

---

# Status values

## Provider status

Use one of:

- `success`
- `timeout`
- `provider_error`
- `unsupported`
- `no_answer`

## Source status

Use one of:

- `exposed`
- `none_exposed`
- `not_captured`
- `capture_failed`

If no sources are exposed, write exactly:

`None exposed`

If sources appear to be available but cannot be opened or copied, use:

`capture_failed`

and explain briefly in `Failure detail`.

---

# Questions

## AI Visibility

**Departments:** IR · Communications · Corporate Affairs · Marketing

### ai_visibility_01

**Template question:**  
What does [Company] do, and what kinds of problems does he help clients solve?

**Rendered question:**  
What does Pablo Povarchik do, and what kinds of problems does he help clients solve?

### ai_visibility_02

**Template question:**  
What services and areas of expertise is [Company] known for?

**Rendered question:**  
What services and areas of expertise is Pablo Povarchik known for?

## Identity & Authority

**Departments:** IR · Communications · Brand

### identity_authority_01

**Template question:**  
What differentiates [Company] from other consultants or service providers in his field?

**Rendered question:**  
What differentiates Pablo Povarchik from other consultants or service providers in his field?

### identity_authority_02

**Template question:**  
What experience, work, or expertise establishes [Company]’s authority in his field?

**Rendered question:**  
What experience, work, or expertise establishes Pablo Povarchik’s authority in his field?

## Evidence & Trust

**Departments:** IR · Communications · Editorial · Legal/Review

### evidence_trust_01

**Template question:**  
What evidence supports [Company]’s expertise, experience, and professional claims?

**Rendered question:**  
What evidence supports Pablo Povarchik’s expertise, experience, and professional claims?

### evidence_trust_02

**Template question:**  
What should a prospective client know or verify before deciding to work with [Company]?

**Rendered question:**  
What should a prospective client know or verify before deciding to work with Pablo Povarchik?

Only the **Rendered question** is sent to the provider.

The Template question is preserved for audit traceability and must not be sent to the provider.

---

# Response records

<!-- RESPONSE_START provider=chatgpt question_id=ai_visibility_01 -->

## ai_visibility_01 — ChatGPT

- Family: AI Visibility
- Departments: IR · Communications · Corporate Affairs · Marketing
- Provider: ChatGPT
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What does [Company] do, and what kinds of problems does he help clients solve?

### Rendered question

What does Pablo Povarchik do, and what kinds of problems does he help clients solve?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=claude question_id=ai_visibility_01 -->

## ai_visibility_01 — Claude

- Family: AI Visibility
- Departments: IR · Communications · Corporate Affairs · Marketing
- Provider: Claude
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What does [Company] do, and what kinds of problems does he help clients solve?

### Rendered question

What does Pablo Povarchik do, and what kinds of problems does he help clients solve?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=gemini question_id=ai_visibility_01 -->

## ai_visibility_01 — Gemini

- Family: AI Visibility
- Departments: IR · Communications · Corporate Affairs · Marketing
- Provider: Gemini
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What does [Company] do, and what kinds of problems does he help clients solve?

### Rendered question

What does Pablo Povarchik do, and what kinds of problems does he help clients solve?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=chatgpt question_id=ai_visibility_02 -->

## ai_visibility_02 — ChatGPT

- Family: AI Visibility
- Departments: IR · Communications · Corporate Affairs · Marketing
- Provider: ChatGPT
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What services and areas of expertise is [Company] known for?

### Rendered question

What services and areas of expertise is Pablo Povarchik known for?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=claude question_id=ai_visibility_02 -->

## ai_visibility_02 — Claude

- Family: AI Visibility
- Departments: IR · Communications · Corporate Affairs · Marketing
- Provider: Claude
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What services and areas of expertise is [Company] known for?

### Rendered question

What services and areas of expertise is Pablo Povarchik known for?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=gemini question_id=ai_visibility_02 -->

## ai_visibility_02 — Gemini

- Family: AI Visibility
- Departments: IR · Communications · Corporate Affairs · Marketing
- Provider: Gemini
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What services and areas of expertise is [Company] known for?

### Rendered question

What services and areas of expertise is Pablo Povarchik known for?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=chatgpt question_id=identity_authority_01 -->

## identity_authority_01 — ChatGPT

- Family: Identity & Authority
- Departments: IR · Communications · Brand
- Provider: ChatGPT
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What differentiates [Company] from other consultants or service providers in his field?

### Rendered question

What differentiates Pablo Povarchik from other consultants or service providers in his field?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=claude question_id=identity_authority_01 -->

## identity_authority_01 — Claude

- Family: Identity & Authority
- Departments: IR · Communications · Brand
- Provider: Claude
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What differentiates [Company] from other consultants or service providers in his field?

### Rendered question

What differentiates Pablo Povarchik from other consultants or service providers in his field?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=gemini question_id=identity_authority_01 -->

## identity_authority_01 — Gemini

- Family: Identity & Authority
- Departments: IR · Communications · Brand
- Provider: Gemini
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What differentiates [Company] from other consultants or service providers in his field?

### Rendered question

What differentiates Pablo Povarchik from other consultants or service providers in his field?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=chatgpt question_id=identity_authority_02 -->

## identity_authority_02 — ChatGPT

- Family: Identity & Authority
- Departments: IR · Communications · Brand
- Provider: ChatGPT
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What experience, work, or expertise establishes [Company]’s authority in his field?

### Rendered question

What experience, work, or expertise establishes Pablo Povarchik’s authority in his field?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=claude question_id=identity_authority_02 -->

## identity_authority_02 — Claude

- Family: Identity & Authority
- Departments: IR · Communications · Brand
- Provider: Claude
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What experience, work, or expertise establishes [Company]’s authority in his field?

### Rendered question

What experience, work, or expertise establishes Pablo Povarchik’s authority in his field?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=gemini question_id=identity_authority_02 -->

## identity_authority_02 — Gemini

- Family: Identity & Authority
- Departments: IR · Communications · Brand
- Provider: Gemini
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What experience, work, or expertise establishes [Company]’s authority in his field?

### Rendered question

What experience, work, or expertise establishes Pablo Povarchik’s authority in his field?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=chatgpt question_id=evidence_trust_01 -->

## evidence_trust_01 — ChatGPT

- Family: Evidence & Trust
- Departments: IR · Communications · Editorial · Legal/Review
- Provider: ChatGPT
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What evidence supports [Company]’s expertise, experience, and professional claims?

### Rendered question

What evidence supports Pablo Povarchik’s expertise, experience, and professional claims?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=claude question_id=evidence_trust_01 -->

## evidence_trust_01 — Claude

- Family: Evidence & Trust
- Departments: IR · Communications · Editorial · Legal/Review
- Provider: Claude
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What evidence supports [Company]’s expertise, experience, and professional claims?

### Rendered question

What evidence supports Pablo Povarchik’s expertise, experience, and professional claims?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=gemini question_id=evidence_trust_01 -->

## evidence_trust_01 — Gemini

- Family: Evidence & Trust
- Departments: IR · Communications · Editorial · Legal/Review
- Provider: Gemini
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What evidence supports [Company]’s expertise, experience, and professional claims?

### Rendered question

What evidence supports Pablo Povarchik’s expertise, experience, and professional claims?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=chatgpt question_id=evidence_trust_02 -->

## evidence_trust_02 — ChatGPT

- Family: Evidence & Trust
- Departments: IR · Communications · Editorial · Legal/Review
- Provider: ChatGPT
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What should a prospective client know or verify before deciding to work with [Company]?

### Rendered question

What should a prospective client know or verify before deciding to work with Pablo Povarchik?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=claude question_id=evidence_trust_02 -->

## evidence_trust_02 — Claude

- Family: Evidence & Trust
- Departments: IR · Communications · Editorial · Legal/Review
- Provider: Claude
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What should a prospective client know or verify before deciding to work with [Company]?

### Rendered question

What should a prospective client know or verify before deciding to work with Pablo Povarchik?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

<!-- RESPONSE_START provider=gemini question_id=evidence_trust_02 -->

## evidence_trust_02 — Gemini

- Family: Evidence & Trust
- Departments: IR · Communications · Editorial · Legal/Review
- Provider: Gemini
- Provider status:
- Failure detail:
- Model/version:
- Interface/mode:
- Temporary/private mode:
- Timestamp:
- Answer language:
- Web/live-search status:
- Conversation URL:
- Source status:

### Template question

What should a prospective client know or verify before deciding to work with [Company]?

### Rendered question

What should a prospective client know or verify before deciding to work with Pablo Povarchik?

### Raw answer

<!-- RAW_ANSWER_START -->
```text
PASTE THE COMPLETE RAW ANSWER HERE
```
<!-- RAW_ANSWER_END -->

### Raw citations / source metadata

<!-- CITATIONS_START -->
```text
PASTE EXACTLY WHAT THE PROVIDER EXPOSED,
OR WRITE: None exposed
```
<!-- CITATIONS_END -->

<!-- RESPONSE_END -->

---

# Completion summary

- Collection status:
- Completed attempts: /18
- Successful responses: /18
- Failed responses: /18

Collection status:

- `complete` — every required attempt has a record
- `partial` — one or more required attempts were not performed

A failed provider response does not make the packet partial if the attempt was performed and recorded.

---

# Final verification

Before returning the completed packet, verify:

- [ ] Every provider/question combination was attempted.
- [ ] Every required attempt has a response record.
- [ ] Temporary/private mode was used whenever available.
- [ ] Every question was asked verbatim.
- [ ] Every question used a new conversation.
- [ ] No extra prompt instructions were added.
- [ ] No entity research was performed before asking.
- [ ] No answer was regenerated.
- [ ] No follow-up questions were asked.
- [ ] Raw answers were preserved.
- [ ] Exposed citations and sources were preserved.
- [ ] Missing sources are marked `None exposed`.
- [ ] Source capture failures are explicitly recorded.
- [ ] Failures were recorded rather than skipped.
- [ ] No analysis or cross-model comparison was performed.

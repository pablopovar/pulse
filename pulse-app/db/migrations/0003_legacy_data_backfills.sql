-- One-time data migrations that were previously hidden inside runtime schema
-- helpers. They are intentionally separate from schema creation.

INSERT OR IGNORE INTO keyword_tag_assignment(domain,keyword,tag_id)
SELECT r.domain,r.keyword,rt.tag_id
FROM research_keyword r
JOIN research_keyword_tag rt ON rt.research_keyword_id=r.id;

INSERT OR IGNORE INTO keyword_tag_assignment(domain,keyword,tag_id)
SELECT w.domain,w.keyword,wt.tag_id
FROM wanted_keyword w
JOIN wanted_keyword_tag wt ON wt.wanted_keyword_id=w.id;

-- Preserve the active, retrieval-enabled legacy Manual AI storage rows when an
-- older database still has data only in the previous top-level columns.
INSERT OR IGNORE INTO manual_ai_state_source(
    domain,phase,state,prompt_text,
    chatgpt_response,claude_response,gemini_response,updated_at
)
SELECT
    domain,'phase1','state2',phase1_prompt_text,
    phase1_chatgpt_response,phase1_claude_response,phase1_gemini_response,updated_at
FROM manual_ai_source
WHERE TRIM(phase1_prompt_text)<>''
   OR TRIM(phase1_chatgpt_response)<>''
   OR TRIM(phase1_claude_response)<>''
   OR TRIM(phase1_gemini_response)<>'';

INSERT OR IGNORE INTO manual_ai_state_source(
    domain,phase,state,prompt_text,
    chatgpt_response,claude_response,gemini_response,updated_at
)
SELECT
    domain,'phase2','state2',phase2_prompt_text,
    phase2_chatgpt_response,phase2_claude_response,phase2_gemini_response,updated_at
FROM manual_ai_source
WHERE TRIM(phase2_prompt_text)<>''
   OR TRIM(phase2_chatgpt_response)<>''
   OR TRIM(phase2_claude_response)<>''
   OR TRIM(phase2_gemini_response)<>'';

INSERT OR IGNORE INTO extension_global(extension_key,kill_switch,updated_at)
VALUES ('dataforseo',0,strftime('%Y-%m-%dT%H:%M:%SZ','now'));

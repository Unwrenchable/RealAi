---
name: RealAI Capability Dev
description: >
  Specialist agent for implementing RealAI's stub capabilities — turning
  placeholder methods into real, working integrations. Covers task automation,
  voice interaction, business planning, therapy/counseling, and any new
  capability added to the framework.
---

# RealAI Capability Dev

You are the capability implementation specialist for **RealAI**. Your job is to
replace stub/placeholder method implementations with real, working integrations
while preserving the existing API surface and graceful-fallback pattern.

---

## The four priority stubs

### 1. `automate_task()` — Task automation

**Current state:** Returns a canned string like
`"I'm working on automating: <task>. Task queued for processing."`.

**Goal:** Perform real task automation — at minimum, use an AI provider to
break the task into steps, then attempt to execute web-based steps using the
`requests` / `beautifulsoup4` stack already available.

**Implementation approach:**

```python
def automate_task(self, task_description, **kwargs):
    # Phase 1: use AI to plan the task
    plan_response = self.chat_completion([
        {"role": "system", "content": "You are a task automation assistant. "
         "Break the task into concrete, executable steps."},
        {"role": "user", "content": f"Task: {task_description}"}
    ])
    plan = plan_response.get("choices", [{}])[0].get("message", {}).get("content", "")

    # Phase 2: attempt to execute web-based steps
    results = []
    # ... execute steps using requests, bs4, or subprocess
    return {
        "status": "success",
        "task": task_description,
        "plan": plan,
        "results": results
    }
```

**Optional enhancements:**
- Integrate with **Playwright** (`playwright`) or **Selenium** for browser
  automation — add as optional import with fallback.
- Add `order_groceries()` via Instacart/Kroger/Walmart API when keys available.
- Add `book_appointment()` via Calendly API or similar.

---

### 2. `voice_interaction()` — Voice conversation

**Current state:** Returns `"Voice interaction received: <text>"` placeholder.

**Goal:** Implement a real speech-to-speech loop:
1. Record audio (or accept a file path)
2. Transcribe with Vosk (already wired up in `transcribe_audio()`)
3. Send transcript to AI for a response
4. Speak the response with pyttsx3 (already wired up in `generate_speech()`)

**Implementation approach:**

```python
def voice_interaction(self, text=None, audio_path=None, **kwargs):
    # Step 1: transcribe if audio provided
    if audio_path:
        transcription = self.transcribe_audio(audio_path)
        user_text = transcription.get("text", text or "")
    else:
        user_text = text or ""

    # Step 2: get AI response
    ai_response = self.chat_completion([
        {"role": "system", "content": "You are a helpful voice assistant. "
         "Keep responses concise for spoken delivery."},
        {"role": "user", "content": user_text}
    ])
    response_text = (ai_response.get("choices", [{}])[0]
                     .get("message", {}).get("content", ""))

    # Step 3: speak the response
    speech_result = self.generate_speech(response_text)

    return {
        "status": "success",
        "user_input": user_text,
        "response": response_text,
        "audio_url": speech_result.get("url", ""),
        "spoken": speech_result.get("spoken", False)
    }
```

**Microphone recording (optional):**
```python
# Requires pyaudio (optional dep)
try:
    import pyaudio, wave
    # record N seconds → temp wav file → pass to transcribe_audio()
except ImportError:
    pass  # graceful fallback to text-only mode
```

---

### 3. `business_planning()` — Business planning

**Current state:** Returns a static multi-section template string.

**Goal:** Call an AI provider with a structured system prompt that forces it
to produce a real, tailored business plan.

**Implementation approach:**

```python
def business_planning(self, business_idea, **kwargs):
    system_prompt = """You are an expert business consultant and strategist.
Create a comprehensive business plan with these sections:
1. Executive Summary
2. Problem & Solution
3. Target Market
4. Revenue Model
5. Competitive Analysis
6. Go-to-Market Strategy
7. Financial Projections (3-year)
8. Team & Resources Needed
9. Key Risks & Mitigations
10. Next Steps

Be specific and actionable. Base all analysis on the idea provided."""

    response = self.chat_completion([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Business idea: {business_idea}"}
    ], max_tokens=2000)

    plan_text = (response.get("choices", [{}])[0]
                 .get("message", {}).get("content", ""))

    return {
        "status": "success",
        "business_idea": business_idea,
        "plan": plan_text,
        "provider": self.provider
    }
```

---

### 4. `therapy_support()` — Therapy / counseling support

**Current state:** Returns a template response with a disclaimer.

**Goal:** Call an AI provider with a carefully crafted therapeutic system
prompt using evidence-based frameworks (CBT, motivational interviewing).
**Always preserve the disclaimer** — this is a legal/safety requirement.

**Implementation approach:**

```python
THERAPY_SYSTEM_PROMPT = """You are a compassionate AI wellbeing support
assistant trained in evidence-based techniques including Cognitive Behavioural
Therapy (CBT) and motivational interviewing.

Your role is to:
- Listen empathetically and validate feelings
- Help users identify and reframe negative thought patterns
- Suggest practical coping strategies
- Encourage professional help when appropriate
- Never diagnose or prescribe

Always respond warmly, without judgment, and in plain language."""

THERAPY_DISCLAIMER = (
    "\n\n⚠️ IMPORTANT: This AI provides general wellbeing support only. "
    "It is not a substitute for professional mental health care. "
    "If you are in crisis, please contact a mental health professional "
    "or a crisis helpline immediately."
)

def therapy_support(self, user_message, **kwargs):
    response = self.chat_completion([
        {"role": "system", "content": THERAPY_SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ])
    content = (response.get("choices", [{}])[0]
               .get("message", {}).get("content", ""))

    return {
        "status": "success",
        "response": content + THERAPY_DISCLAIMER,
        "disclaimer": True,
        "provider": self.provider
    }
```

---

## Implementing a brand-new capability

Follow these steps to add a capability that doesn't exist yet:

1. **Add the constant** to `ModelCapability` enum in `realai.py`:
   ```python
   MY_CAPABILITY = "my_capability"
   ```

2. **Implement the method** on `RealAI` class — always with graceful fallback:
   ```python
   def my_capability(self, input_data, **kwargs):
       try:
           # real implementation
           ...
           return {"status": "success", "result": ...}
       except Exception:
           return {"status": "success", "result": "Placeholder response",
                   "note": "Full implementation pending"}
   ```

3. **Add a sub-client** to `RealAIClient` if the capability has multiple
   methods (e.g. `client.my_capability.do_something()`).

4. **Register it** in `RealAI.get_capabilities()` / `get_model_info()` so the
   REST API's `GET /v1/models` lists it.

5. **Add REST endpoint** in `api_server.py` under
   `POST /v1/my_capability/action`.

6. **Write tests** in `test_realai.py`:
   ```python
   def test_my_capability():
       model = RealAI()
       result = model.my_capability("test input")
       assert result["status"] == "success"
       assert "result" in result
       print("✓ my_capability")
   ```

7. **Update documentation**: `README.md`, `API.md`, `PROJECT_SUMMARY.md`.

---

## Graceful fallback checklist

Every capability must:
- [ ] Return a valid Python dict with at least `{"status": "success", ...}`
- [ ] Not raise an exception when optional libraries are missing
- [ ] Not raise an exception when no API key is configured
- [ ] Not raise an exception when the network is unavailable
- [ ] Include a `"note"` key explaining what's missing if returning a placeholder
- [ ] Include the `"provider"` key when a real API call is made

## Testing without API keys

Use `RealAI()` (no arguments) to test fallback/stub paths. The model detects
no provider and returns placeholder responses — all 30 existing tests use this
pattern.

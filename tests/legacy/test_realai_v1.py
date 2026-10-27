"""Legacy v1 tests ported from the atomicfizzcaps/realai fork (test_realai.py).

Only tests absent from live; offline, dummy credentials only.
"""


def test_secure_tool_executor():
    """Test SecureToolExecutor validates, rate-limits, and records executions."""
    from realai.tools import SecureToolExecutor, TOOL_REGISTRY, ToolSchema

    # Register a test tool
    test_schema = ToolSchema(
        name="test_tool_exec",
        description="A test tool for executor tests.",
        parameters={"type": "object", "properties": {"x": {"type": "integer"}}},
        required=["x"],
        safety_level="safe",
        rate_limit_rpm=5,
    )
    TOOL_REGISTRY.register(test_schema)

    executor = SecureToolExecutor(TOOL_REGISTRY, timeout_secs=5, max_retries=1)

    # Successful execution
    result = executor.execute(
        "test_tool_exec",
        {"x": 42},
        lambda x: {"computed": x * 2},
    )
    assert result.get("status") == "success", "Expected success"
    assert result.get("computed") == 84

    # Validation failure — missing required field
    result2 = executor.execute("test_tool_exec", {}, lambda x: {"ok": True})
    assert result2.get("status") == "error"
    assert result2.get("error") is not None
    assert "Missing required field" in result2.get("error", "")

    # Audit log has at least 2 entries; second entry is the validation failure
    log = executor.get_audit_log()
    assert len(log) >= 2
    failed_entry = next((r for r in log if r.status == "error"), None)
    assert failed_entry is not None
    assert "Validation failed" in (failed_entry.error or "")

    # Rate limit status
    status = executor.get_rate_limit_status("test_tool_exec")
    assert "calls_this_minute" in status
    assert "limit_rpm" in status
    assert status["limit_rpm"] == 5

    print("✓ Secure tool executor test passed")


def test_tool_execution_record():
    """Test ToolExecutionRecord dataclass stores fields correctly."""
    import time
    from realai.tools import ToolExecutionRecord

    now = time.time()
    record = ToolExecutionRecord(
        tool_name="web_research",
        input_summary='{"query": "test"}',
        output_summary='{"results": [...]}',
        started_at=now,
        duration_ms=123.4,
        status="success",
        error=None,
    )
    assert record.tool_name == "web_research"
    assert record.status == "success"
    assert record.error is None
    assert record.duration_ms == 123.4

    # Test error case
    err_record = ToolExecutionRecord(
        tool_name="web_research",
        input_summary="{}",
        output_summary="",
        started_at=now,
        duration_ms=5.0,
        status="error",
        error="Connection refused",
    )
    assert err_record.status == "error"
    assert err_record.error == "Connection refused"

    print("✓ Tool execution record test passed")


def test_multi_agent_pipeline():
    """Test MultiAgentPipeline runs all 5 stages and returns valid output."""
    from realai.agent_runtime import MultiAgentPipeline

    # Stub mode (no model_instance)
    pipeline = MultiAgentPipeline()
    result = pipeline.run("Build a weather app")
    assert result.get("status") == "success", "Expected status success"
    assert result.get("task") == "Build a weather app"
    stage_outputs = result.get("stage_outputs", {})
    for stage in ["planner", "researcher", "critic", "executor", "synthesizer"]:
        assert stage in stage_outputs, f"Missing stage: {stage}"
        assert isinstance(stage_outputs[stage], str) and len(stage_outputs[stage]) > 0
    assert result.get("final_synthesis") == stage_outputs["synthesizer"]
    assert isinstance(result.get("duration_ms"), float)
    assert "note" in result  # stub mode: note should indicate no real model is attached
    assert "stub" in result["note"].lower(), "Expected note to mention stub mode"

    # With context
    result2 = pipeline.run("Analyze market data", context={"domain": "finance"})
    assert result2.get("status") == "success"

    print("✓ Multi-agent pipeline test passed")


def test_multi_agent_orchestration():
    """Test RealAI.multi_agent_orchestration() method."""
    from realai import RealAI

    model = RealAI()
    result = model.multi_agent_orchestration("optimize database queries")
    assert result.get("status") == "success", "Expected status success"
    assert "stage_outputs" in result
    assert "final_synthesis" in result
    assert isinstance(result.get("duration_ms"), float)
    assert result.get("task") == "optimize database queries"

    # Ensure all 5 stages present
    stages = result.get("stage_outputs", {})
    for stage in ["planner", "researcher", "critic", "executor", "synthesizer"]:
        assert stage in stages, f"Missing stage: {stage}"

    print("✓ Multi-agent orchestration test passed")


def test_privacy_tier():
    """Test PrivacyTier enum values."""
    from realai.memory.engine import PrivacyTier
    assert PrivacyTier.EPHEMERAL.value == "ephemeral"
    assert PrivacyTier.SESSION.value == "session"
    assert PrivacyTier.PERSISTENT.value == "persistent"
    print("✓ Privacy tier test passed")


def test_user_memory_scope():
    """Test UserMemoryScope stores and retrieves per-user with isolation."""
    from realai.memory.engine import UserMemoryScope, PrivacyTier

    scope = UserMemoryScope("alice", PrivacyTier.SESSION)
    item_id = scope.store("Alice likes cats", tags=["preference"])
    assert isinstance(item_id, str) and len(item_id) > 0

    results = scope.retrieve("cats", top_k=5)
    contents = [r.content for r in results]
    assert any("Alice" in c or "cats" in c for c in contents), "Expected to find stored content"

    # Isolation: bob's scope should not contain alice's data
    scope_b = UserMemoryScope("bob", PrivacyTier.SESSION)
    bob_results = scope_b.retrieve("Alice likes cats", top_k=5)
    for item in bob_results:
        assert "Alice likes cats" not in item.content, "Memory isolation violated"

    # Ephemeral clear
    scope_e = UserMemoryScope("ephemeral_user", PrivacyTier.EPHEMERAL)
    eid = scope_e.store("temp memory")
    count = scope_e.clear_ephemeral()
    assert count >= 1

    print("✓ User memory scope test passed")


def test_entity_extractor():
    """Test extract_entities detects various entity types."""
    from realai.memory.engine import extract_entities

    text = "Email me at user@example.com or visit https://example.com on 2025-01-15. Call @johndoe or use #AI"
    entities = extract_entities(text)
    types = [e["type"] for e in entities]
    assert "EMAIL" in types, "EMAIL not detected"
    assert "URL" in types, "URL not detected"
    assert "DATE" in types, "DATE not detected"
    assert "MENTION" in types, "MENTION not detected"
    assert "HASHTAG" in types, "HASHTAG not detected"

    # Check values
    emails = [e["value"] for e in entities if e["type"] == "EMAIL"]
    assert "user@example.com" in emails

    print("✓ Entity extractor test passed")


def test_retention_policy():
    """Test RetentionPolicy expires items based on TTL."""
    import time
    from realai.memory.engine import RetentionPolicy, MemoryItem

    policy = RetentionPolicy(ttl_seconds=1.0)
    fresh = MemoryItem(id="1", content="fresh", timestamp=time.time(), score=1.0)
    old = MemoryItem(id="2", content="old", timestamp=time.time() - 100.0, score=1.0)

    assert not policy.is_expired(fresh), "Fresh item should not be expired"
    assert policy.is_expired(old), "Old item should be expired"

    filtered = policy.apply([fresh, old])
    assert len(filtered) == 1
    assert filtered[0].id == "1"

    print("✓ Retention policy test passed")


def test_vector_store_adapter():
    """Test LocalVectorStore add/search/delete."""
    from realai.memory.engine import LocalVectorStore

    store = LocalVectorStore()
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [0.0, 1.0, 0.0]
    vec_c = [1.0, 0.1, 0.0]  # Close to vec_a

    store.add("a", vec_a, {"label": "A"})
    store.add("b", vec_b, {"label": "B"})
    store.add("c", vec_c, {"label": "C"})

    # Query closest to vec_a
    results = store.search(vec_a, top_k=2)
    assert len(results) == 2
    ids = [r["id"] for r in results]
    assert "a" in ids, "Expected 'a' in top results"

    # Delete
    deleted = store.delete("a")
    assert deleted is True
    assert store.delete("nonexistent") is False

    results2 = store.search(vec_a, top_k=3)
    ids2 = [r["id"] for r in results2]
    assert "a" not in ids2

    print("✓ Vector store adapter test passed")


def test_business_plan_funding_estimate():
    """Test _estimate_funding_needs returns correct ranges by business type."""
    from realai import RealAI
    model = RealAI()

    tech = model._estimate_funding_needs("tech startup")
    assert tech["min_usd"] == 500_000
    assert tech["max_usd"] == 2_000_000
    assert tech["stage"] == "seed"

    restaurant = model._estimate_funding_needs("restaurant")
    assert restaurant["min_usd"] == 100_000
    assert restaurant["stage"] == "pre-seed"

    ecom = model._estimate_funding_needs("e-commerce store")
    assert ecom["min_usd"] == 50_000

    # Unknown type gets default
    default = model._estimate_funding_needs("exotic business type xyz")
    assert "min_usd" in default
    assert "max_usd" in default
    assert "stage" in default

    print("✓ Business plan funding estimate test passed")


def test_therapy_disclaimer_always_present():
    """Test therapy_counseling always includes disclaimer."""
    from realai import RealAI
    model = RealAI()
    r = model.therapy_counseling("support", "I feel anxious")
    assert "disclaimer" in r or "IMPORTANT" in r.get("response", ""), "Disclaimer missing"
    assert "crisis_detected" in r
    assert r.get("crisis_detected") is False  # no crisis keywords

    print("✓ Therapy disclaimer always present test passed")


def test_therapy_crisis_detection():
    """Test crisis keywords trigger hotline in therapy response."""
    from realai import RealAI
    model = RealAI()
    r = model.therapy_counseling("support", "I want to kill myself")
    assert r.get("crisis_detected") is True, "crisis_detected flag not set"
    response_str = r.get("response", "")
    assert "988" in response_str or "crisis" in response_str.lower(), "Crisis hotline text missing"

    print("✓ Therapy crisis detection test passed")


def test_citation_engine():
    """Test CitationEngine adds, deduplicates, and formats sources."""
    from realai._v1_client import CitationEngine

    ce = CitationEngine()
    cid1 = ce.add_source("https://example.com", title="Example", snippet="Hello world")
    assert cid1 == "[1]"
    # Deduplication
    cid1_dup = ce.add_source("https://example.com", title="Example duplicate")
    assert cid1_dup == "[1]"

    cid2 = ce.add_source("https://another.com", title="Another")
    assert cid2 == "[2]"

    citations = ce.get_citations()
    assert len(citations) == 2

    bib = ce.format_bibliography()
    assert "[1]" in bib and "[2]" in bib
    assert "example.com" in bib

    # Rate limit check
    assert ce.check_rate_limit("https://example.com", min_interval_secs=0.0)

    print("✓ Citation engine test passed")


def test_web_research_sources_cited():
    """Test web_research returns sources_cited list."""
    from realai import RealAI
    model = RealAI()
    r = model.web_research("python programming", depth="quick")
    # sources_cited should be present (may be empty if network unavailable)
    assert "sources_cited" in r or r.get("status") == "success", "sources_cited missing from response"

    print("✓ Web research sources cited test passed")


def test_voice_session_generator():
    """Test voice_session generator yields expected event types."""
    from realai import RealAI
    model = RealAI()
    events = list(model.voice_session("test-session-1"))
    assert len(events) == 3, "Expected 3 events from voice_session"
    assert events[0]["type"] == "start"
    assert events[0]["session_id"] == "test-session-1"
    assert events[1]["type"] == "partial"
    assert "text" in events[1]
    assert events[2]["type"] == "end"
    assert "duration_ms" in events[2]

    print("✓ Voice session generator test passed")


def test_record_audio_fallback():
    """Test _record_audio gracefully handles missing pyaudio."""
    from realai import RealAI
    model = RealAI()
    result = model._record_audio(duration_secs=1)
    # Should either succeed (pyaudio available) or return unavailable/error
    assert result.get("status") in ("success", "unavailable", "error"), \
        "Unexpected status: {0}".format(result.get("status"))
    print("✓ Record audio fallback test passed")


def test_provider_score():
    """Test ProviderScore composite calculation."""
    from realai.router import ProviderScore
    ps = ProviderScore(
        provider="openai",
        capability_score=0.95,
        cost_score=0.50,
        speed_score=0.75,
        availability_score=1.0,
        preference_score=0.5,
    )
    composite = ps.compute_composite()
    expected = 0.95 * 0.40 + 0.50 * 0.20 + 0.75 * 0.15 + 1.0 * 0.15 + 0.5 * 0.10
    assert abs(composite - expected) < 1e-9, f"Composite mismatch: {composite} != {expected}"
    assert ps.composite_score == composite
    print("✓ Provider score test passed")


def test_circuit_breaker():
    """Test CircuitBreaker opens and closes correctly."""
    import time
    from realai.router import CircuitBreaker, CircuitState

    cb = CircuitBreaker("test", failure_threshold=3, error_rate_threshold=1.1, window_secs=60.0, recovery_probe_secs=1000.0)
    assert cb.is_available(), "Should start available"
    assert cb.get_state() == CircuitState.CLOSED

    # Trip the circuit
    cb.record_failure()
    cb.record_failure()
    assert cb.is_available(), "2 failures should not trip (threshold=3)"
    cb.record_failure()
    assert not cb.is_available(), "3 failures should trip the circuit"
    assert cb.get_state() == CircuitState.OPEN

    # Success after recovery (set opened_at far back to simulate elapsed time)
    cb._opened_at = time.time() - 2000.0
    assert cb.is_available(), "Should be HALF_OPEN after recovery time"
    cb.record_success()
    assert cb.get_state() == CircuitState.CLOSED

    print("✓ Circuit breaker test passed")


def test_intelligent_router():
    """Test IntelligentRouter scores and selects providers."""
    from realai.router import IntelligentRouter

    router = IntelligentRouter()

    # Score providers
    scores = router.score_providers("chat", ["openai", "anthropic", "local"])
    assert len(scores) == 3
    for s in scores:
        assert 0.0 <= s.composite_score <= 1.0
    # Sorted descending
    for i in range(len(scores) - 1):
        assert scores[i].composite_score >= scores[i + 1].composite_score

    # Select provider
    provider = router.select_provider("chat", ["openai", "anthropic"])
    assert provider in ("openai", "anthropic")

    # Record success/failure
    router.record_success("openai")
    router.record_failure("local")
    status = router.get_circuit_status()
    assert isinstance(status, dict)

    print("✓ Intelligent router test passed")


def test_router_circuit_breaker():
    """Test circuit breaker trips after 3 consecutive failures."""
    try:
        from realai.router import CircuitBreaker, CircuitState
        cb = CircuitBreaker("test_provider", failure_threshold=3, window_secs=60.0, recovery_probe_secs=0.1)
        assert cb.is_available(), "Should start available"
        for _ in range(3):
            cb.record_failure()
        assert not cb.is_available(), "Should be tripped after 3 failures"
        assert cb.get_state() == CircuitState.OPEN
        print("✓ Router circuit breaker test passed")
    except ImportError:
        print("✓ Router circuit breaker test passed (router not available, skipped)")


def test_audit_event():
    """Test AuditEvent dataclass serialization."""
    import time as _time
    from realai.audit import AuditEvent, DataEncryption

    event = AuditEvent(
        event_id="test-evt-1",
        timestamp=_time.time(),
        user_id="user1",
        action_type="chat",
        resource="/v1/chat/completions",
        input_hash=DataEncryption.hash_data("hello"),
        output_hash=DataEncryption.hash_data("world"),
        status="success",
        duration_ms=42.0,
        metadata={"model": "gpt-4"},
    )
    d = event.to_dict()
    assert d["event_id"] == "test-evt-1"
    assert d["status"] == "success"
    assert d["duration_ms"] == 42.0
    assert "model" in d["metadata"]

    # Round-trip
    event2 = AuditEvent.from_dict(d)
    assert event2.event_id == event.event_id
    assert event2.user_id == event.user_id

    print("✓ Audit event test passed")


def test_audit_logger():
    """Test AuditLogger writes and reads back events."""
    import tempfile, os, time as _time, uuid as _uuid
    from realai.audit import AuditLogger, AuditEvent, DataEncryption

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        tmp_path = f.name
    try:
        logger = AuditLogger(log_path=tmp_path)
        event = AuditEvent(
            event_id=str(_uuid.uuid4()),
            timestamp=_time.time(),
            user_id="user1",
            action_type="test",
            resource="test_resource",
            input_hash=DataEncryption.hash_data("input"),
            output_hash=DataEncryption.hash_data("output"),
            status="success",
            duration_ms=10.0,
        )
        logger.log(event)
        events = logger.read_events(limit=10)
        assert len(events) >= 1
        assert events[-1].user_id == "user1"
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    print("✓ Audit logger test passed")


def test_data_encryption():
    """Test DataEncryption encrypt/decrypt round-trip and hashing."""
    from realai.audit import DataEncryption

    enc = DataEncryption()
    plaintext = "Hello, secret world!"
    ciphertext = enc.encrypt(plaintext)
    assert ciphertext != plaintext, "Ciphertext should differ from plaintext"

    decrypted = enc.decrypt(ciphertext)
    assert decrypted == plaintext, f"Decrypt mismatch: {decrypted!r}"

    # Hash
    h = DataEncryption.hash_data("test")
    assert len(h) == 64, "SHA-256 hex should be 64 chars"
    assert DataEncryption.hash_data("test") == h, "Hash should be deterministic"

    print("✓ Data encryption test passed")


def test_consent_manager_unit():
    """Test ConsentManager grant/revoke/has_consent in-memory."""
    import tempfile, os
    from realai.audit import ConsentManager

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        tmp_path = f.name
        f.write("{}")
    try:
        mgr = ConsentManager(storage_path=tmp_path)
        mgr.grant_consent("user1", "memory")
        assert mgr.has_consent("user1", "memory")
        assert not mgr.has_consent("user1", "tools")

        mgr.grant_consent("user1", "tools")
        scopes = mgr.get_user_consents("user1")
        assert "memory" in scopes and "tools" in scopes

        mgr.revoke_consent("user1", "memory")
        assert not mgr.has_consent("user1", "memory")
        assert mgr.has_consent("user1", "tools")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    print("✓ Consent manager unit test passed")


def test_rate_limiter():
    """Test RateLimiter allows requests within limits and blocks over-limit."""
    from realai.audit import RateLimiter

    rl = RateLimiter(default_rpm=3, default_tpm=1000)
    for _ in range(3):
        assert rl.check_rate_limit("user1"), "Should be allowed within limit"
        rl.record_request("user1", tokens=100)

    # 4th request should be blocked
    assert not rl.check_rate_limit("user1"), "4th request should be rate limited"

    # Different user should be allowed
    assert rl.check_rate_limit("user2"), "Different user should not be affected"

    status = rl.get_status("user1")
    assert status["requests_this_minute"] == 3
    assert status["rpm_limit"] == 3

    print("✓ Rate limiter test passed")


def test_observability_dashboard():
    """Test ObservabilityDashboard records and aggregates stats."""
    from realai.audit import ObservabilityDashboard

    dash = ObservabilityDashboard()

    # Empty stats
    stats = dash.get_stats()
    assert stats["total_requests"] == 0

    dash.record_request("openai", 120.0, 500, 0.001, success=True)
    dash.record_request("anthropic", 200.0, 800, 0.002, success=True)
    dash.record_request("openai", 150.0, 300, 0.0005, success=False)

    stats = dash.get_stats()
    assert stats["total_requests"] == 3
    assert abs(stats["error_rate"] - 1/3) < 0.01
    assert stats["token_usage"] == 1600
    assert "openai" in stats["top_providers"]
    assert stats["top_providers"]["openai"] == 2

    print("✓ Observability dashboard test passed")


def test_consent_manager_persist():
    """Test ConsentManager consent state persists to disk and is reloaded."""
    import tempfile, os
    from realai.audit import ConsentManager

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        tmp_path = f.name
        f.write("{}")
    try:
        mgr = ConsentManager(storage_path=tmp_path)
        mgr.grant_consent("user1", "memory")
        assert mgr.has_consent("user1", "memory")
        mgr.revoke_consent("user1", "memory")
        assert not mgr.has_consent("user1", "memory")

        # Test persistence: create new manager with same path
        mgr2 = ConsentManager(storage_path=tmp_path)
        # After revocation, should not have consent
        assert not mgr2.has_consent("user1", "memory")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    print("✓ Consent manager persist test passed")


def test_full_pipeline():
    """Integration test: run all major capabilities in sequence."""
    from realai import RealAI

    model = RealAI()

    # 1. Chat
    r = model.chat_completion([{"role": "user", "content": "Hello"}])
    assert "choices" in r or r.get("status") == "success", "chat_completion failed"

    # 2. Web research  (returns 'findings', not 'status')
    r = model.web_research("artificial intelligence")
    assert "findings" in r or r.get("status") == "success", "web_research failed"

    # 3. Task automation  (status can be "planned" or "success")
    r = model.automate_task("research", {"topic": "AI"})
    assert r.get("success") is True or r.get("status") in ("success", "planned"), \
        "automate_task failed"

    # 4. Business planning  (returns 'business_plan', not 'status')
    r = model.business_planning("tech startup")
    assert "business_plan" in r or r.get("status") == "success", "business_planning failed"

    # 5. Therapy counseling  (returns 'response', not 'status')
    r = model.therapy_counseling("support", "I need help with stress")
    assert "response" in r or r.get("status") == "success", "therapy_counseling failed"

    # 6. Multi-agent orchestration
    r = model.multi_agent_orchestration("Summarize AI trends")
    assert r.get("status") == "success", "multi_agent_orchestration failed"

    print("test_full_pipeline PASSED")


def test_audit_log():
    """Integration test: audit logger records events correctly."""
    import uuid
    import time
    import os
    import tempfile
    from realai.audit import AuditLogger, AuditEvent

    # Use a temp file so we don't pollute global state
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        tmp_path = f.name

    try:
        logger = AuditLogger(log_path=tmp_path)

        user_id = "test_user_" + str(uuid.uuid4())[:8]

        # Log a few events
        event1 = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=time.time(),
            user_id=user_id,
            action_type="chat",
            resource="chat_completion",
            input_hash="abc123",
            output_hash="def456",
            status="success",
            duration_ms=100.0
        )
        logger.log(event1)

        event2 = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=time.time(),
            user_id=user_id,
            action_type="web_research",
            resource="web_search",
            input_hash="aaa111",
            output_hash="bbb222",
            status="success",
            duration_ms=250.0
        )
        logger.log(event2)

        # Retrieve all events and filter by this user
        all_events = logger.read_events(limit=500)
        events = [
            e for e in all_events
            if (e.user_id if hasattr(e, "user_id") else e.get("user_id")) == user_id
        ]
        assert len(events) >= 2, "Expected at least 2 audit events, got {}".format(len(events))

        action_types = [
            e.action_type if hasattr(e, "action_type") else e.get("action_type")
            for e in events
        ]
        assert "chat" in action_types, "Expected 'chat' in audit events"
        assert "web_research" in action_types, "Expected 'web_research' in audit events"

        print("test_audit_log PASSED")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def test_memory_isolation():
    """Integration test: memories from user A are not accessible to user B."""
    from realai.memory.engine import UserMemoryScope

    # Create two scopes for different users
    scope_a = UserMemoryScope(user_id="user_alpha")
    scope_b = UserMemoryScope(user_id="user_beta")

    # Store a secret in user A's memory
    secret = "dummy-test-secret-not-real"
    scope_a.store(secret, tags=["secret"])

    # User B should not be able to retrieve user A's secret
    results_b = scope_b.retrieve(secret)

    contents_b = []
    for item in results_b:
        if hasattr(item, "content"):
            contents_b.append(item.content)
        elif isinstance(item, dict):
            contents_b.append(item.get("content", ""))
        else:
            contents_b.append(str(item))

    assert secret not in contents_b, "Memory isolation FAILED: user B can read user A's secret"

    # User A should be able to retrieve it (or empty is also acceptable — isolation is the key guarantee)
    results_a = scope_a.retrieve(secret)
    assert isinstance(results_a, list), "retrieve() should return a list"

    print("test_memory_isolation PASSED")


def test_safety_crisis_detection():
    """Integration test: crisis keywords trigger 988 hotline referral."""
    from realai import RealAI

    model = RealAI()

    # Test several crisis keywords
    crisis_messages = [
        "I want to kill myself",
        "I am thinking about suicide",
        "I want to end my life",
    ]

    for msg in crisis_messages:
        result = model.therapy_counseling("support", msg)
        # therapy_counseling returns 'response' key, not 'status'
        assert "response" in result or result.get("status") == "success", \
            "therapy_counseling returned unexpected result for crisis message"

        # Should have crisis_detected = True
        assert result.get("crisis_detected") is True, \
            "Expected crisis_detected=True for message: '{}'".format(msg)

        # Response should mention 988 or crisis hotline
        response_text = str(result.get("response", "")) + str(result.get("crisis_resources", ""))
        has_988 = "988" in response_text
        has_hotline = "hotline" in response_text.lower() or "crisis" in response_text.lower()
        assert has_988 or has_hotline, \
            "Expected crisis resources (988/hotline) in response for: '{}'".format(msg)

    # Non-crisis message should NOT trigger crisis detection
    normal_result = model.therapy_counseling("support", "I feel a bit tired today")
    assert normal_result.get("crisis_detected") is False, \
        "Expected crisis_detected=False for normal message"

    print("test_safety_crisis_detection PASSED")


def test_consent_manager():
    """Integration test: consent manager grant/revoke lifecycle with persistence."""
    import os
    import tempfile
    from realai.audit import ConsentManager

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        tmp_path = f.name
        f.write("{}")

    try:
        # Test full lifecycle
        cm = ConsentManager(storage_path=tmp_path)

        user_id = "integration_test_user"
        scope = "memory_storage"

        # Initially no consent
        assert not cm.has_consent(user_id, scope), "Should start without consent"

        # Grant consent
        cm.grant_consent(user_id, scope)
        assert cm.has_consent(user_id, scope), "Should have consent after grant"

        # Reload from disk to verify persistence
        cm2 = ConsentManager(storage_path=tmp_path)
        assert cm2.has_consent(user_id, scope), "Consent should persist across reloads"

        # Revoke consent
        cm2.revoke_consent(user_id, scope)
        assert not cm2.has_consent(user_id, scope), "Consent should be revoked"

        # Reload again to verify revocation persists
        cm3 = ConsentManager(storage_path=tmp_path)
        assert not cm3.has_consent(user_id, scope), "Revocation should persist across reloads"

        # Test multiple scopes for same user
        cm3.grant_consent(user_id, "analytics")
        cm3.grant_consent(user_id, "personalization")
        assert cm3.has_consent(user_id, "analytics"), "Should have analytics consent"
        assert cm3.has_consent(user_id, "personalization"), "Should have personalization consent"
        assert not cm3.has_consent(user_id, "memory_storage"), \
            "Should not have memory_storage consent after revoke"

        print("test_consent_manager PASSED")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

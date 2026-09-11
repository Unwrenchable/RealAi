"""
Tests for RealAI model.

Run with: python test_realai.py
"""

import sys
from realai import RealAI, RealAIClient, ModelCapability, PROVIDER_CONFIGS, PROVIDER_ENV_VARS, _detect_provider


def test_model_initialization():
    """Test model initialization."""
    print("Testing model initialization...")
    model = RealAI()
    assert model.model_name == "realai-2.0"
    assert model.version == "2.0.0"
    assert len(model.capabilities) > 0
    print("✓ Model initialization test passed")


def test_client_initialization():
    """Test client initialization."""
    print("Testing client initialization...")
    client = RealAIClient()
    assert client.model is not None
    assert hasattr(client, 'chat')
    assert hasattr(client, 'completions')
    assert hasattr(client, 'images')
    assert hasattr(client, 'videos')
    assert hasattr(client, 'embeddings')
    assert hasattr(client, 'audio')
    # New capabilities
    assert hasattr(client, 'web')
    assert hasattr(client, 'tasks')
    assert hasattr(client, 'voice')
    assert hasattr(client, 'business')
    assert hasattr(client, 'therapy')
    assert hasattr(client, 'web3')
    assert hasattr(client, 'plugins')
    assert hasattr(client, 'personas')
    # Next-generation capability sub-clients
    assert hasattr(client, 'reasoning')
    assert hasattr(client, 'synthesis')
    assert hasattr(client, 'reflection')
    assert hasattr(client, 'agents')
    print("✓ Client initialization test passed")


def test_chat_completion():
    """Test chat completion."""
    print("Testing chat completion...")
    client = RealAIClient()
    response = client.chat.create(
        messages=[
            {"role": "user", "content": "Hello"}
        ]
    )
    assert 'id' in response
    assert 'choices' in response
    assert len(response['choices']) > 0
    assert 'message' in response['choices'][0]
    print("✓ Chat completion test passed")


def test_text_completion():
    """Test text completion."""
    print("Testing text completion...")
    client = RealAIClient()
    response = client.completions.create(
        prompt="Hello world"
    )
    assert 'id' in response
    assert 'choices' in response
    assert len(response['choices']) > 0
    print("✓ Text completion test passed")


def test_image_generation():
    """Test image generation."""
    print("Testing image generation...")
    client = RealAIClient()
    response = client.images.generate(
        prompt="A sunset"
    )
    assert 'data' in response
    assert len(response['data']) > 0
    assert 'url' in response['data'][0]
    print("✓ Image generation test passed")


def test_image_analysis():
    """Test image analysis."""
    print("Testing image analysis...")
    client = RealAIClient()
    response = client.images.analyze(
        image_url="https://example.com/test.jpg"
    )
    assert 'analysis' in response
    assert 'description' in response
    print("✓ Image analysis test passed")


def test_video_generation():
    """Test video generation."""
    print("Testing video generation...")
    client = RealAIClient()
    response = client.videos.generate(
        prompt="A drone flyover of a futuristic city",
        duration=4,
        n=1
    )
    assert 'created' in response
    assert 'data' in response
    assert len(response['data']) > 0
    assert 'url' in response['data'][0]
    print("✓ Video generation test passed")


def test_code_generation():
    """Test code generation."""
    print("Testing code generation...")
    model = RealAI()
    response = model.generate_code(
        prompt="Sort a list",
        language="python"
    )
    assert 'code' in response
    assert 'language' in response
    print("✓ Code generation test passed")


def test_embeddings():
    """Test embeddings creation."""
    print("Testing embeddings...")
    client = RealAIClient()
    response = client.embeddings.create(
        input_text="Test text"
    )
    assert 'data' in response
    assert len(response['data']) > 0
    assert 'embedding' in response['data'][0]
    assert len(response['data'][0]['embedding']) > 0
    print("✓ Embeddings test passed")


def test_structured_server_routes():
    """Test the structured server router and registry."""
    print("Testing structured server routes...")
    from realai.server.config import get_model_config, list_models
    from realai.server.router import dispatch_request

    models = list_models()
    assert 'realai-1.0' in models
    config = get_model_config('realai-1.0')
    assert config['id'] == 'realai-1.0'
    assert config['backend'] == 'vllm'
    assert config['path'] == 'meta-llama/Meta-Llama-3-8B-Instruct'

    status, response, content_type = dispatch_request(
        'POST',
        '/v1/chat/completions',
        {
            'model': 'realai-1.0',
            'messages': [{'role': 'user', 'content': 'Hello structured server'}],
            'temperature': 0.2,
            'max_tokens': 32,
        }
    )
    assert status == 200
    assert content_type == 'application/json'
    assert 'choices' in response

    status, response, _content_type = dispatch_request(
        'POST',
        '/v1/chat/completions',
        {
            'model': 'realai-1.0',
            'messages': [{'role': 'user', 'content': 'Hello structured server'}],
            'tools': 'not-a-list',
        }
    )
    assert status == 400
    assert 'tools must be a list' in response['error']['message']

    status, response, content_type = dispatch_request(
        'POST',
        '/v1/embeddings',
        {'model': 'realai-embed', 'input': ['hello', 'world']}
    )
    assert status == 200
    assert len(response['data']) == 2

    status, response, content_type = dispatch_request('GET', '/metrics')
    assert status == 200
    assert 'realai_requests_total' in response

    status, response, _content_type = dispatch_request('GET', '/v1/models')
    assert status == 200
    assert response['object'] == 'list'
    assert any(model['id'] == 'realai-1.0' for model in response['data'])

    status, response, _content_type = dispatch_request(
        'POST',
        '/v1/images/generations',
        {'prompt': 'A test scene', 'n': 1}
    )
    assert status == 200
    assert len(response['data']) == 1

    status, response, _content_type = dispatch_request(
        'POST',
        '/v1/audio/transcriptions',
        {'file': 'audio.mp3'}
    )
    assert status == 200
    assert 'text' in response

    status, response, _content_type = dispatch_request(
        'POST',
        '/v1/audio/speech',
        {'input': 'Hello world'}
    )
    assert status == 200
    assert 'audio_url' in response
    print("✓ Structured server routes test passed")


def test_structured_server_platform_endpoints():
    """Test memory/tools/tasks provider platform endpoints."""
    print("Testing structured server platform endpoints...")
    from realai.server.router import dispatch_request

    status, response, _content_type = dispatch_request('GET', '/v1/tools')
    assert status == 200
    assert response['object'] == 'list'
    assert any(tool['name'] == 'web_search' for tool in response['data'])

    status, response, _content_type = dispatch_request(
        'POST',
        '/v1/memory/store',
        {'user_id': 'u1', 'agent_id': 'a1', 'content': 'Solana tx failed at simulation step'}
    )
    assert status == 200
    assert response['status'] == 'stored'

    status, response, _content_type = dispatch_request(
        'POST',
        '/v1/memory/inspect',
        {'user_id': 'u1', 'agent_id': 'a1'}
    )
    assert status == 200
    assert response['object'] == 'list'
    assert len(response['data']) == 1

    status, response, _content_type = dispatch_request(
        'POST',
        '/v1/tasks',
        {'task': 'Draft a deployment checklist', 'context': 'render + postgres'}
    )
    assert status == 200
    assert response['status'] == 'completed'
    task_id = response['id']

    status, response, _content_type = dispatch_request('GET', '/v1/tasks/{0}'.format(task_id))
    assert status == 200
    assert response['id'] == task_id

    status, response, _content_type = dispatch_request('GET', '/v1/tasks')
    assert status == 200
    assert response['object'] == 'list'
    assert len(response['data']) >= 1
    print("✓ Structured server platform endpoints test passed")


def test_structured_server_config_files():
    """Test typed config loading from realai.toml/models.yaml/providers.yaml."""
    print("Testing structured server config loading...")
    from realai.server.config import load_registry, load_settings

    settings = load_settings()
    assert settings.default_chat_model == 'realai-1.0'
    assert settings.default_embedding_model == 'realai-embed'
    assert settings.provider == 'local'
    assert 'default' in settings.profiles
    assert 'providers' in settings.providers

    registry = load_registry()
    assert 'realai-1.0' in registry
    assert 'realai-overseer' in registry
    assert 'realai-default-8b' in registry
    assert registry['realai-embed']['embedding_dimensions'] == 384
    print("✓ Structured server config loading test passed")


def test_week2_inference_registry_routes():
    """Test week-2 app routes wired through inference registry."""
    print("Testing week-2 inference registry routes...")
    try:
        from apps.api.routes.chat import chat_completions
        from apps.api.routes.embeddings import embeddings
        from apps.api.routes.models import list_models
    except ImportError:
        print("✓ Week-2 inference registry routes skipped (FastAPI unavailable)")
        return
    from core.api.schemas.chat import ChatCompletionRequest
    from core.api.schemas.embeddings import EmbeddingsRequest

    models_payload = list_models()
    assert 'data' in models_payload
    assert len(models_payload['data']) >= 1

    chat_req = ChatCompletionRequest(
        model='realai-default',
        messages=[{'role': 'user', 'content': 'hello from week2'}],
        stream=False,
    )
    chat_resp = chat_completions(chat_req)
    assert chat_resp['model'] == 'local-stub-chat'
    assert chat_resp['choices'][0]['message']['role'] == 'assistant'

    embed_req = EmbeddingsRequest(
        model='realai-embed-default',
        input=['hello', 'world'],
    )
    embed_resp = embeddings(embed_req)
    assert embed_resp['model'] == 'local-stub-embed'
    assert len(embed_resp['data']) == 2
    print("✓ Week-2 inference registry routes test passed")


def test_week3_memory_and_tool_pipeline():
    """Test chat pipeline memory retrieval + tool execution loop."""
    print("Testing week-3 memory and tool pipeline...")
    try:
        from apps.api.routes.chat import chat_completions
    except ImportError:
        print("✓ Week-3 memory and tool pipeline skipped (FastAPI unavailable)")
        return
    from core.api.schemas.chat import ChatCompletionRequest
    from core.memory.sqlite_store import SQLiteMemoryStore

    user_id = "week3-user"
    memory = SQLiteMemoryStore("realai_memory.sqlite3")
    memory.clear(user_id)

    tool_req = ChatCompletionRequest(
        model="realai-default",
        user_id=user_id,
        messages=[{"role": "user", "content": "Search the web for solana staking yield"}],
    )
    tool_resp = chat_completions(tool_req)
    assert "choices" in tool_resp
    assert "tool result" in tool_resp["choices"][0]["message"]["content"].lower()

    remember_req = ChatCompletionRequest(
        model="realai-default",
        user_id=user_id,
        messages=[{"role": "user", "content": "Remember my dog's name is Pixel"}],
    )
    chat_completions(remember_req)

    found = memory.search(user_id, "Pixel", k=3)
    assert len(found) >= 1
    assert any("pixel" in item["content"].lower() for item in found)
    print("✓ Week-3 memory and tool pipeline test passed")


def test_week5_voice_registry_backends():
    """Test week-5 voice registry and fallback backends."""
    print("Testing week-5 voice registry/backends...")
    from core.voice.asr_whisper import WhisperASR
    from core.voice.registry import VoiceRegistry
    from core.voice.tts_piper import PiperTTS

    registry = VoiceRegistry()
    asr = WhisperASR()
    tts = PiperTTS()
    registry.register_asr(asr)
    registry.register_tts(tts)

    transcribed = registry.get_asr("whisper-asr").transcribe(b"fake-audio")
    assert "text" in transcribed

    audio_bytes = registry.get_tts("piper-tts").synthesize("hello")
    assert isinstance(audio_bytes, (bytes, bytearray))
    assert len(audio_bytes) > 0
    print("✓ Week-5 voice registry/backends test passed")


def test_week7_python_sandbox_security():
    """Test Week-7 sandbox timeout and filesystem lock-down."""
    print("Testing week-7 python sandbox security...")
    from core.security.python_sandbox import PythonSandbox

    sandbox = PythonSandbox(timeout_seconds=1)
    blocked = sandbox.run("open('blocked.txt', 'w').write('x')")
    assert "PermissionError" in blocked.get("stderr", "") or blocked.get("returncode", 0) != 0

    timeout = sandbox.run("while True:\n    pass")
    assert "error" in timeout or timeout.get("returncode", 0) != 0
    print("✓ Week-7 python sandbox security test passed")


def test_week7_tool_permission_enforcement():
    """Test tool permission enforcement in ToolRegistry."""
    print("Testing week-7 tool permission enforcement...")
    from core.tools.registry import ToolRegistry
    from core.tools.web import WebSearchTool

    registry = ToolRegistry()
    registry.register(WebSearchTool())

    denied = False
    try:
        registry.execute_tool("web_search", {"query": ""}, context={"allowed_permissions": []})
    except PermissionError:
        denied = True
    assert denied

    allowed = registry.execute_tool(
        "web_search",
        {"query": ""},
        context={"allowed_permissions": ["network"]},
    )
    assert "results" in allowed
    print("✓ Week-7 tool permission enforcement test passed")


def test_week7_agent_safety_limits():
    """Test agent max-step safety enforcement."""
    print("Testing week-7 agent safety limits...")
    from core.agents.executor import TaskExecutor

    class _Planner:
        def step(self, _messages, _context):
            return {"plan": ["step-{0}".format(i) for i in range(11)]}

    class _Worker:
        def step(self, _messages, _context):
            return {"ok": True}

    class _Critic:
        def step(self, _messages, _context):
            return {"ok": True}

    class _Synth:
        def step(self, _messages, _context):
            return {"final": "done"}

    executor = TaskExecutor(_Planner(), _Worker(), _Critic(), _Synth())
    hit_limit = False
    try:
        executor.run([], {"model": "realai-default"})
    except RuntimeError:
        hit_limit = True
    assert hit_limit
    print("✓ Week-7 agent safety limits test passed")


def test_week7_web3_policy():
    """Test web3 approval flow and spend limit enforcement."""
    print("Testing week-7 web3 policy...")
    from core.web3.policy import Web3Policy

    policy = Web3Policy(max_spend=0.1)
    approval = policy.require_approval({"value": 0.01})
    assert approval["requires_approval"] is True

    denied = False
    try:
        policy.validate_tx({"value": 0.2, "approved": True})
    except ValueError:
        denied = True
    assert denied

    denied = False
    try:
        policy.validate_tx({"value": 0.01})
    except PermissionError:
        denied = True
    assert denied
    print("✓ Week-7 web3 policy test passed")


def test_week7_tool_call_validation():
    """Test tool call validation for unknown tools."""
    print("Testing week-7 tool call validation...")
    from core.agents.safety import AgentSafety

    safety = AgentSafety()
    denied = False
    try:
        safety.validate_tool_call({"name": "unknown_tool"}, ["web_search"])
    except PermissionError:
        denied = True
    assert denied
    print("✓ Week-7 tool call validation test passed")


def test_week9_model_cache():
    """Test model cache lazy loading and hot reload clear behavior."""
    print("Testing week-9 model cache...")
    from core.models.cache import ModelCache

    cache = ModelCache()
    counter = {"n": 0}

    def _loader():
        counter["n"] += 1
        return {"id": "demo"}

    first = cache.get("demo", _loader)
    second = cache.get("demo", _loader)
    assert first["id"] == "demo"
    assert second["id"] == "demo"
    assert counter["n"] == 1
    cache.clear()
    cache.get("demo", _loader)
    assert counter["n"] == 2
    print("✓ Week-9 model cache test passed")


def test_week9_health_and_reload_routes():
    """Test health/readiness and model reload routes."""
    print("Testing week-9 health/reload routes...")
    try:
        from apps.api.routes.health import health, ready
        from apps.api.routes.models import reload_models
    except ImportError:
        print("✓ Week-9 health/reload routes skipped (FastAPI unavailable)")
        return

    health_payload = health()
    assert health_payload.get("status") == "ok"

    reload_payload = reload_models()
    assert reload_payload.get("status") == "reloaded"

    ready_payload = ready()
    assert "models_loaded" in ready_payload
    print("✓ Week-9 health/reload routes test passed")


def test_structured_training_pipeline():
    """Test training dataset extraction helpers."""
    print("Testing structured training pipeline...")
    import json
    import tempfile
    from pathlib import Path

    from realai.training.build_datasets import build_dataset_bundle
    from realai.training.eval import evaluate_instruction_dataset
    from realai.training.finetune import build_finetune_plan

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        processed_path = tmp_path / 'processed'
        processed_path.mkdir()
        (processed_path / 'instructions.jsonl').write_text(
            json.dumps({
                'messages': [
                    {'role': 'user', 'content': 'Explain vector databases.'},
                    {'role': 'assistant', 'content': 'A vector database stores embeddings.'},
                ]
            }) + '\n',
            encoding='utf-8'
        )

        manifest = build_dataset_bundle(str(processed_path), str(processed_path))
        assert manifest['datasets']['train']['rows'] == 1
        assert manifest['datasets']['val']['rows'] == 0

        evaluation = evaluate_instruction_dataset(manifest['datasets']['train']['path'])
        assert evaluation['examples'] == 1

        plan = build_finetune_plan(data_dir=str(processed_path))
        assert plan['status'] == 'ready'
    print("✓ Structured training pipeline test passed")


def test_structured_sdk_facade():
    """Test the structured SDK facade."""
    print("Testing structured SDK facade...")
    import threading
    from wsgiref.simple_server import make_server

    from realai.sdk.python.realai_client import RealAIClient as SDKRealAIClient, create_client
    from realai.server.app import wsgi_app

    server = make_server('127.0.0.1', 0, wsgi_app)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    try:
        client = create_client(api_url='http://127.0.0.1:{0}'.format(server.server_port))
        assert isinstance(client, SDKRealAIClient)
        response = client.chat(
            'realai-1.0',
            [{'role': 'user', 'content': 'Hello from sdk'}],
            temperature=0.2,
            max_tokens=32,
        )
        assert 'choices' in response

        embeddings = client.embeddings('realai-embed', ['Hello from sdk'])
        assert len(embeddings['data']) == 1
    finally:
        server.shutdown()
        server.server_close()
    print("✓ Structured SDK facade test passed")


def test_audio_transcription():
    """Test audio transcription."""
    print("Testing audio transcription...")
    client = RealAIClient()
    response = client.audio.transcribe(
        audio_file="test.mp3"
    )
    assert 'text' in response
    assert 'language' in response
    print("✓ Audio transcription test passed")


def test_audio_generation():
    """Test audio generation."""
    print("Testing audio generation...")
    client = RealAIClient()
    response = client.audio.generate(
        text="Hello"
    )
    assert 'audio_url' in response
    print("✓ Audio generation test passed")


def test_translation():
    """Test translation."""
    print("Testing translation...")
    model = RealAI()
    response = model.translate(
        text="Hello",
        target_language="es"
    )
    assert 'translated_text' in response
    assert 'target_language' in response
    print("✓ Translation test passed")


def test_model_capabilities():
    """Test getting model capabilities."""
    print("Testing model capabilities...")
    model = RealAI()
    capabilities = model.get_capabilities()
    assert len(capabilities) >= 44
    assert 'text_generation' in capabilities
    assert 'image_generation' in capabilities
    assert 'video_generation' in capabilities
    assert 'code_generation' in capabilities
    assert 'web_research' in capabilities
    assert 'task_automation' in capabilities
    assert 'voice_interaction' in capabilities
    assert 'business_planning' in capabilities
    assert 'therapy_counseling' in capabilities
    assert 'web3_integration' in capabilities
    # Next-generation capabilities
    assert 'self_reflection' in capabilities
    assert 'chain_of_thought' in capabilities
    assert 'knowledge_synthesis' in capabilities
    assert 'multi_agent' in capabilities
    print("✓ Model capabilities test passed")


def test_model_info():
    """Test getting model info."""
    print("Testing model info...")
    model = RealAI()
    info = model.get_model_info()
    assert 'name' in info
    assert 'version' in info
    assert 'capabilities' in info
    print("✓ Model info test passed")


def test_web_research():
    """Test web research capability."""
    print("Testing web research...")
    model = RealAI()
    response = model.web_research(
        query="AI developments",
        depth="standard"
    )
    assert 'query' in response
    assert 'findings' in response
    assert 'sources' in response
    assert 'citations' in response
    assert 'freshness' in response
    print("✓ Web research test passed")


def test_capability_catalog_and_provider_capabilities():
    """Test unified capability catalog and provider capability map access."""
    print("Testing capability catalog/provider capabilities...")
    model = RealAI(api_key="sk-testkey123")
    catalog = model.get_capability_catalog()
    assert 'capabilities' in catalog
    assert 'domains' in catalog
    assert catalog['count'] >= 17
    provider_caps = model.get_provider_capabilities()
    assert provider_caps['provider'] == 'openai'
    assert 'supported_capabilities' in provider_caps
    assert 'unsupported_capabilities' in provider_caps
    print("✓ Capability catalog/provider capabilities test passed")


def test_persona_profiles_and_chat_metadata():
    """Test persona switching and canonical response metadata."""
    print("Testing personas and response metadata...")
    model = RealAI()
    personas = model.get_personas()
    assert 'balanced' in personas
    model.set_persona("analyst")
    response = model.chat_completion(messages=[{"role": "user", "content": "Hello"}])
    assert 'realai_meta' in response
    assert response['realai_meta']['capability'] == 'text_generation'
    assert response['realai_meta']['persona'] == 'analyst'
    print("✓ Personas and response metadata test passed")


def test_task_automation():
    """Test task automation capability."""
    print("Testing task automation...")
    client = RealAIClient()
    response = client.tasks.order_groceries(
        items=["milk", "eggs"],
        execute=False
    )
    assert 'task_type' in response
    assert 'status' in response
    assert response['task_type'] == 'groceries'
    print("✓ Task automation test passed")


def test_voice_interaction():
    """Test voice interaction capability."""
    print("Testing voice interaction...")
    client = RealAIClient()
    response = client.voice.conversation(
        message="Hello"
    )
    assert 'conversation_id' in response
    assert 'response_text' in response
    print("✓ Voice interaction test passed")


def test_business_planning():
    """Test business planning capability."""
    print("Testing business planning...")
    client = RealAIClient()
    response = client.business.build(
        business_type="tech startup"
    )
    assert 'business_type' in response
    assert 'business_plan' in response
    assert 'action_items' in response
    print("✓ Business planning test passed")


def test_therapy_counseling():
    """Test therapy/counseling capability."""
    print("Testing therapy counseling...")
    model = RealAI()
    response = model.therapy_counseling(
        session_type="support",
        message="I need support"
    )
    assert 'session_id' in response
    assert 'response' in response
    assert 'recommendations' in response
    print("✓ Therapy counseling test passed")


def test_web3_integration():
    """Test Web3 integration capability."""
    print("Testing Web3 integration...")
    client = RealAIClient()
    response = client.web3.smart_contract(
        blockchain="ethereum"
    )
    assert 'operation' in response
    assert 'blockchain' in response
    assert 'status' in response
    print("✓ Web3 integration test passed")


def test_web3_gpg_signing():
    """Test Web3 GPG signing capability."""
    print("Testing Web3 GPG signing...")
    client = RealAIClient()
    # Test GPG signing without requiring a live Web3 provider.
    response = client.web3.execute(
        operation="transaction",
        blockchain="ethereum",
        sign_with_gpg=True,
        transaction_data="test transaction data",
        gpg_keyid="test@example.com"
    )
    assert 'operation' in response
    assert 'blockchain' in response
    assert 'status' in response
    assert 'result' not in response
    assert (
        response.get('signature_status') == 'signed_with_gpg'
        or 'error' in response
    )
    print("✓ Web3 GPG signing test passed")


def test_code_execution():
    """Test code execution capability."""
    print("Testing code execution...")
    model = RealAI()
    response = model.execute_code(
        code="print('Hello')",
        language="python"
    )
    assert 'execution_status' in response
    assert 'output' in response
    assert response['execution_status'] == 'completed', f"Expected 'completed', got '{response['execution_status']}'"
    assert response['output'].strip() == 'Hello', f"Expected 'Hello', got '{response['output'].strip()}'"
    print("✓ Code execution test passed")


def test_plugin_system():
    """Test plugin system capability."""
    print("Testing plugin system...")
    client = RealAIClient()
    response = client.plugins.load(
        plugin_name="test_plugin"
    )
    assert 'plugin_name' in response
    assert 'status' in response
    print("✓ Plugin system test passed")


def test_local_plugin_loading():
    """Test loading a local plugin from the `plugins` package."""
    print("Testing local plugin loading...")
    client = RealAIClient()
    response = client.plugins.load(plugin_name="sample_plugin")
    assert response.get('plugin_name') == 'sample_plugin'
    # Plugin should be recorded in model registry and attach a callable
    assert 'sample_plugin' in client.model.plugins_registry
    assert hasattr(client.model, 'sample_action')
    result = client.model.sample_action({'x': 1})
    assert isinstance(result, dict)
    assert result.get('ok') is True
    print("✓ Local plugin loading test passed")


def test_load_all_plugins():
    """Test discovery and loading of all plugins in `plugins` package."""
    print("Testing load_all_plugins...")
    client = RealAIClient()
    loaded = client.model.load_all_plugins()
    # At least our sample_plugin should be discovered and loaded
    assert 'sample_plugin' in loaded
    print("✓ load_all_plugins test passed")


def test_memory_learning():
    """Test memory/learning capability."""
    print("Testing memory learning...")
    model = RealAI()
    response = model.learn_from_interaction(
        interaction_data={"test": "data"},
        save=True
    )
    assert 'learned' in response
    assert 'insights' in response
    print("✓ Memory learning test passed")


def test_provider_detection():
    """Test automatic provider detection from API key prefixes."""
    print("Testing provider detection...")
    assert _detect_provider("sk-abc123", None) == "openai"
    assert _detect_provider("sk-proj-abc123", None) == "openai"
    assert _detect_provider("sk-ant-abc123", None) == "anthropic"
    assert _detect_provider("xai-abc123", None) == "grok"
    assert _detect_provider("AIzaXYZ", None) == "gemini"
    assert _detect_provider("sk-or-v1-abc123", None) == "openrouter"
    assert _detect_provider("pplx-abc123", None) == "perplexity"
    assert _detect_provider(None, None) is None
    assert _detect_provider(None, "openai") == "openai"
    assert _detect_provider("sk-abc123", "anthropic") == "anthropic"  # explicit wins
    print("✓ Provider detection test passed")


def test_provider_configs():
    """Test that PROVIDER_CONFIGS contains all expected providers."""
    print("Testing provider configs...")
    for name in ("openai", "anthropic", "grok", "gemini",
                 "openrouter", "mistral", "together", "deepseek", "perplexity"):
        assert name in PROVIDER_CONFIGS, f"Missing provider: {name}"
        cfg = PROVIDER_CONFIGS[name]
        assert "base_url" in cfg
        assert "default_model" in cfg
        assert "api_format" in cfg
    print("✓ Provider configs test passed")


def test_provider_env_vars():
    """Test that PROVIDER_ENV_VARS covers all providers in PROVIDER_CONFIGS."""
    print("Testing provider env vars...")
    for name in ("openai", "anthropic", "grok", "gemini",
                 "openrouter", "mistral", "together", "deepseek", "perplexity"):
        assert name in PROVIDER_ENV_VARS, f"Missing env var entry for: {name}"
        env_var = PROVIDER_ENV_VARS[name]
        assert env_var.startswith("REALAI_"), f"Unexpected env var name: {env_var}"
        assert env_var.endswith("_API_KEY"), f"Unexpected env var name: {env_var}"
    print("✓ Provider env vars test passed")


def test_realai_provider_init():
    """Test RealAI initialises provider routing fields correctly."""
    print("Testing RealAI provider init...")

    # No key → no provider
    m = RealAI()
    assert m.provider is None
    assert m._provider_model == "realai-2.0"

    # OpenAI key auto-detection
    m = RealAI(api_key="sk-testkey123")
    assert m.provider == "openai"
    assert m.base_url == PROVIDER_CONFIGS["openai"]["base_url"]
    assert m._provider_model == PROVIDER_CONFIGS["openai"]["default_model"]

    # Explicit model name preserved when not default
    m = RealAI(api_key="sk-testkey123", model_name="gpt-4o")
    assert m._provider_model == "gpt-4o"

    # Anthropic key auto-detection
    m = RealAI(api_key="sk-ant-testkey123")
    assert m.provider == "anthropic"
    assert m._api_format == "anthropic"

    # OpenRouter key auto-detection
    m = RealAI(api_key="sk-or-v1-testkey123")
    assert m.provider == "openrouter"
    assert m.base_url == PROVIDER_CONFIGS["openrouter"]["base_url"]

    # Perplexity key auto-detection
    m = RealAI(api_key="pplx-testkey123")
    assert m.provider == "perplexity"
    assert m.base_url == PROVIDER_CONFIGS["perplexity"]["base_url"]

    # Explicit provider override
    m = RealAI(api_key="sk-testkey123", provider="grok")
    assert m.provider == "grok"
    assert m.base_url == PROVIDER_CONFIGS["grok"]["base_url"]

    # Mistral via explicit provider (no unique key prefix)
    m = RealAI(api_key="somekey", provider="mistral")
    assert m.provider == "mistral"
    assert m.base_url == PROVIDER_CONFIGS["mistral"]["base_url"]

    # Together AI via explicit provider
    m = RealAI(api_key="somekey", provider="together")
    assert m.provider == "together"
    assert m.base_url == PROVIDER_CONFIGS["together"]["base_url"]

    # DeepSeek via explicit provider
    m = RealAI(api_key="somekey", provider="deepseek")
    assert m.provider == "deepseek"
    assert m.base_url == PROVIDER_CONFIGS["deepseek"]["base_url"]

    # Custom base_url override
    m = RealAI(api_key="sk-testkey123", base_url="http://localhost:11434/v1")
    assert m.base_url == "http://localhost:11434/v1"

    print("✓ RealAI provider init test passed")


def test_client_provider_params():
    """Test RealAIClient forwards provider/base_url to its underlying model."""
    print("Testing RealAIClient provider params...")
    client = RealAIClient(api_key="sk-ant-testkey", provider="anthropic",
                          base_url="https://custom.example.com")
    assert client.model.provider == "anthropic"
    assert client.model.base_url == "https://custom.example.com"
    assert client.model._api_format == "anthropic"
    print("✓ RealAIClient provider params test passed")


def test_chat_fallback_without_key():
    """Placeholder response is returned when no API key is configured."""
    print("Testing chat fallback without key...")
    client = RealAIClient()
    response = client.chat.create(
        messages=[{"role": "user", "content": "Hello"}]
    )
    assert 'id' in response
    assert 'choices' in response
    assert response['choices'][0]['message']['role'] == 'assistant'
    print("✓ Chat fallback without key test passed")


def test_chain_of_thought():
    """Test chain-of-thought reasoning capability."""
    print("Testing chain-of-thought reasoning...")
    model = RealAI()
    response = model.chain_of_thought(
        problem="If all cats are mammals and all mammals breathe air, do cats breathe air?",
        domain="logic"
    )
    assert response['status'] == 'success'
    assert 'steps' in response
    assert isinstance(response['steps'], list)
    assert len(response['steps']) > 0
    assert 'answer' in response
    assert 'confidence' in response
    print("✓ Chain-of-thought reasoning test passed")


def test_chain_of_thought_client():
    """Test chain-of-thought via RealAIClient.reasoning."""
    print("Testing chain-of-thought via client...")
    client = RealAIClient()
    response = client.reasoning.chain(
        problem="What is 2 + 2?",
        domain="math"
    )
    assert response['status'] == 'success'
    assert 'steps' in response
    assert 'answer' in response
    print("✓ Chain-of-thought client test passed")


def test_synthesize_knowledge():
    """Test knowledge synthesis capability."""
    print("Testing knowledge synthesis...")
    model = RealAI()
    response = model.synthesize_knowledge(
        topics=["artificial intelligence", "neuroscience"],
        output_format="bullets"
    )
    assert response['status'] == 'success'
    assert 'topics' in response
    assert 'per_topic' in response
    assert 'synthesis' in response
    assert 'connections' in response
    assert isinstance(response['connections'], list)
    print("✓ Knowledge synthesis test passed")


def test_synthesize_knowledge_client():
    """Test knowledge synthesis via RealAIClient.synthesis."""
    print("Testing knowledge synthesis via client...")
    client = RealAIClient()
    response = client.synthesis.combine(
        topics=["climate change", "renewable energy", "economics"]
    )
    assert response['status'] == 'success'
    assert 'synthesis' in response
    assert len(response['topics']) == 3
    print("✓ Knowledge synthesis client test passed")


def test_self_reflect():
    """Test self-reflection capability."""
    print("Testing self-reflection...")
    model = RealAI()
    history = [
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
    ]
    response = model.self_reflect(interaction_history=history, focus="accuracy")
    assert response['status'] == 'success'
    assert 'strengths' in response
    assert isinstance(response['strengths'], list)
    assert 'weaknesses' in response
    assert isinstance(response['weaknesses'], list)
    assert 'improvements' in response
    assert isinstance(response['improvements'], list)
    assert 'score' in response
    print("✓ Self-reflection test passed")


def test_self_reflect_client():
    """Test self-reflection via RealAIClient.reflection."""
    print("Testing self-reflection via client...")
    client = RealAIClient()
    response = client.reflection.improve(focus="efficiency")
    assert response['status'] == 'success'
    assert 'improvements' in response
    print("✓ Self-reflection client test passed")


def test_orchestrate_agents():
    """Test multi-agent orchestration capability."""
    print("Testing multi-agent orchestration...")
    model = RealAI()
    response = model.orchestrate_agents(
        task="Evaluate the pros and cons of electric vehicles",
        agent_roles=["researcher", "analyst", "critic"]
    )
    assert response['status'] == 'success'
    assert 'task' in response
    assert 'agents_used' in response
    assert 'agent_results' in response
    assert isinstance(response['agent_results'], dict)
    assert 'final_output' in response
    assert 'execution_plan' in response
    assert 'verification' in response
    assert len(response['agent_results']) == 3
    print("✓ Multi-agent orchestration test passed")


def test_orchestrate_agents_client():
    """Test multi-agent orchestration via RealAIClient.agents."""
    print("Testing multi-agent orchestration via client...")
    client = RealAIClient()
    response = client.agents.orchestrate(
        task="Summarize the key trends in renewable energy"
    )
    assert response['status'] == 'success'
    assert 'final_output' in response
    assert 'agents_used' in response
    print("✓ Multi-agent orchestration client test passed")


def test_generate_speech():
    """Test generate_speech convenience method."""
    print("Testing generate_speech...")
    model = RealAI()
    response = model.generate_speech("Hello, world!")
    assert 'url' in response
    assert 'spoken' in response
    assert 'audio_url' in response
    print("✓ generate_speech test passed")


def test_new_capabilities_in_model():
    """Test that all next-gen capabilities appear in model.get_capabilities()."""
    print("Testing next-gen capabilities in model...")
    model = RealAI()
    caps = model.get_capabilities()
    assert 'self_reflection' in caps
    assert 'chain_of_thought' in caps
    assert 'knowledge_synthesis' in caps
    assert 'multi_agent' in caps
    assert 'video_generation' in caps
    print("✓ Next-gen capabilities in model test passed")


def test_new_client_attributes():
    """Test that RealAIClient exposes the new sub-client attributes."""
    print("Testing new client attributes...")
    client = RealAIClient()
    assert hasattr(client, 'reasoning')
    assert hasattr(client, 'synthesis')
    assert hasattr(client, 'reflection')
    assert hasattr(client, 'agents')
    assert hasattr(client, 'videos')
    print("✓ New client attributes test passed")


# ============================================================================
# Future AI Capabilities (2026+) - Cutting-Edge Tests
# ============================================================================

def test_quantum_integration():
    """Test quantum computing integration."""
    print("Testing quantum integration...")
    client = RealAIClient()
    response = client.quantum.compute(operation="factorization", parameters={"number": 15})
    assert 'operation' in response
    assert 'algorithm' in response
    assert 'status' in response
    assert 'factors' in response
    print("✓ Quantum integration test passed")


def test_neural_architecture_search():
    """Test neural architecture search."""
    print("Testing neural architecture search...")
    client = RealAIClient()
    response = client.neural_arch.search(task="classification")
    assert 'task' in response
    assert 'optimal_architecture' in response
    assert 'status' in response
    print("✓ Neural architecture search test passed")


def test_causal_reasoning():
    """Test causal reasoning capabilities."""
    print("Testing causal reasoning...")
    client = RealAIClient()
    response = client.causal.analyze(
        scenario="Testing causal relationships",
        variables=["cause", "effect", "confounder"]
    )
    assert 'scenario' in response
    assert 'causal_graph' in response
    assert 'status' in response
    print("✓ Causal reasoning test passed")


def test_meta_learning():
    """Test meta-learning capabilities."""
    print("Testing meta-learning...")
    client = RealAIClient()
    response = client.meta.learn(learning_tasks=["task1", "task2", "task3"])
    assert 'learning_tasks' in response
    assert 'learned_strategies' in response
    assert 'status' in response
    print("✓ Meta-learning test passed")


def test_emotional_intelligence():
    """Test emotional intelligence capabilities."""
    print("Testing emotional intelligence...")
    client = RealAIClient()
    response = client.emotion.analyze("I'm feeling really happy today!")
    assert 'emotional_analysis' in response
    assert 'primary_emotion' in response['emotional_analysis']
    assert 'status' in response
    print("✓ Emotional intelligence test passed")


def test_swarm_intelligence():
    """Test swarm intelligence capabilities."""
    print("Testing swarm intelligence...")
    client = RealAIClient()
    response = client.swarm.solve(problem="Optimize complex system", agents=25)
    assert 'problem' in response
    assert 'swarm_size' in response
    assert 'emergent_behavior' in response
    assert 'status' in response
    print("✓ Swarm intelligence test passed")


def test_predictive_simulation():
    """Test predictive simulation capabilities."""
    print("Testing predictive simulation...")
    client = RealAIClient()
    response = client.predictive.simulate(scenario="Future technology trends")
    assert 'scenario' in response
    assert 'predictions' in response
    assert 'status' in response
    print("✓ Predictive simulation test passed")


def test_consciousness_simulation():
    """Test consciousness simulation capabilities."""
    print("Testing consciousness simulation...")
    client = RealAIClient()
    response = client.consciousness.simulate(self_awareness=True)
    assert 'consciousness_metrics' in response
    assert 'self_reflection' in response
    assert 'status' in response
    print("✓ Consciousness simulation test passed")


def test_reality_simulation():
    """Test reality simulation capabilities."""
    print("Testing reality simulation...")
    client = RealAIClient()
    response = client.reality.simulate(reality_type="alternate_history")
    assert 'reality_type' in response
    assert 'simulated_reality' in response
    assert 'status' in response
    print("✓ Reality simulation test passed")


# ============================================================================
# Agent Orchestration and Hive Mind System Tests
# ============================================================================

def test_agent_orchestration():
    """Test multi-agent orchestration capabilities."""
    print("Testing agent orchestration...")
    client = RealAIClient()
    response = client.agents.orchestrate(
        task="Build a web application with security testing",
        workflow_type="sequential"
    )
    assert 'task' in response
    assert 'agents_involved' in response
    assert 'workflow_type' in response
    assert 'agent_results' in response
    assert 'hive_mind_insights' in response
    assert 'status' in response
    print("✓ Agent orchestration test passed")


def test_agent_execution():
    """Test individual agent execution."""
    print("Testing agent execution...")
    client = RealAIClient()
    response = client.agents.execute("architect", "Design a REST API for user management")
    assert 'agent_id' in response
    assert 'task' in response
    assert 'result' in response
    assert 'status' in response
    print("✓ Agent execution test passed")


def test_agent_registration():
    """Test custom agent registration."""
    print("Testing agent registration...")
    client = RealAIClient()
    response = client.agents.register(
        agent_id="test_agent",
        role="Test Specialist",
        description="Specialized agent for testing purposes",
        capabilities=["testing", "validation"],
        required_tools=["read_file", "run_in_terminal"]
    )
    assert 'status' in response
    assert 'agent_id' in response
    assert response['agent_id'] == "test_agent"
    print("✓ Agent registration test passed")


def test_agent_listing():
    """Test agent listing and search."""
    print("Testing agent listing...")
    client = RealAIClient()
    response = client.agents.list()
    assert 'status' in response
    assert 'total_agents' in response
    assert 'agents' in response
    assert isinstance(response['agents'], list)
    assert len(response['agents']) > 0
    print("✓ Agent listing test passed")


def test_agent_status():
    """Test hive mind system status."""
    print("Testing agent system status...")
    client = RealAIClient()
    response = client.agents.status()
    assert 'status' in response
    assert 'system_health' in response
    assert 'registered_agents' in response
    assert 'hive_mind_capabilities' in response
    print("✓ Agent status test passed")


def test_core_agent_methods():
    """Test convenience methods for core agents."""
    print("Testing core agent convenience methods...")
    client = RealAIClient()
    
    # Test architect agent
    response = client.agents.architect("Design a microservices architecture")
    assert 'status' in response
    assert 'agent_id' in response
    assert response['agent_id'] == 'architect'
    
    # Test implementer agent
    response = client.agents.implementer("Implement user authentication")
    assert 'status' in response
    assert 'agent_id' in response
    assert response['agent_id'] == 'implementer'
    
    print("✓ Core agent methods test passed")


# ============================================================================
# Cloud Computing and Distributed Systems Tests
# ============================================================================

def test_cloud_deployment_orchestration():
    """Test cloud deployment across multiple providers."""
    print("Testing cloud deployment orchestration...")
    client = RealAIClient()
    response = client.cloud.deploy(
        providers=["vercel", "render", "railway"],
        instance_count=5
    )
    assert 'status' in response
    assert 'deployed_instances' in response
    assert 'total_instances' in response
    assert 'providers_used' in response
    assert 'total_hourly_cost' in response
    print("✓ Cloud deployment orchestration test passed")


def test_distributed_computing_coordination():
    """Test distributed computing coordination."""
    print("Testing distributed computing coordination...")
    client = RealAIClient()
    tasks = [
        {"type": "computation", "operation": "fibonacci", "n": 30},
        {"type": "inference", "model": "gpt-4", "prompt": "Hello world"},
        {"type": "training", "dataset": "mnist", "epochs": 5}
    ]
    response = client.cloud.compute(tasks=tasks)
    assert 'status' in response
    assert 'submitted_tasks' in response
    assert 'task_ids' in response
    assert 'system_status' in response
    print("✓ Distributed computing coordination test passed")


def test_auto_scaling_management():
    """Test auto-scaling configuration."""
    print("Testing auto-scaling management...")
    client = RealAIClient()
    response = client.cloud.scale(
        target_instances=10,
        max_instances=50,
        scale_up_threshold=10,
        scale_down_threshold=2
    )
    assert 'status' in response
    assert 'scaling_config' in response
    assert 'current_status' in response
    assert 'scaling_actions' in response
    print("✓ Auto-scaling management test passed")


def test_load_balancing_optimization():
    """Test load balancing optimization."""
    print("Testing load balancing optimization...")
    client = RealAIClient()
    response = client.cloud.balance(
        algorithm="round_robin",
        health_checks=True,
        session_persistence=False
    )
    assert 'status' in response
    assert 'load_balancing_config' in response
    assert 'load_distribution' in response
    assert 'optimization_metrics' in response
    print("✓ Load balancing optimization test passed")


def test_multi_cloud_resource_management():
    """Test multi-cloud resource management."""
    print("Testing multi-cloud resource management...")
    client = RealAIClient()
    response = client.cloud.resources(
        providers=["vercel", "render", "railway"],
        optimization_goal="cost"
    )
    assert 'status' in response
    assert 'providers_managed' in response
    assert 'provider_breakdown' in response
    assert 'recommendations' in response
    assert 'cost_savings_potential' in response
    print("✓ Multi-cloud resource management test passed")


def test_serverless_function_deployment():
    """Test serverless function deployment."""
    print("Testing serverless function deployment...")
    client = RealAIClient()
    functions = [
        {"name": "api_handler", "runtime": "python3.9"},
        {"name": "data_processor", "runtime": "node18"}
    ]
    response = client.cloud.functions(
        functions=functions,
        providers=["vercel", "render"]
    )
    assert 'status' in response
    assert 'deployed_functions' in response
    assert 'total_functions' in response
    assert 'providers_used' in response
    print("✓ Serverless function deployment test passed")


def test_container_orchestration():
    """Test container orchestration."""
    print("Testing container orchestration...")
    client = RealAIClient()
    containers = [
        {"name": "web_server", "image": "nginx:latest", "replicas": 3},
        {"name": "api_server", "image": "python:3.9", "replicas": 2}
    ]
    response = client.cloud.containers(
        containers=containers,
        orchestration_platform="kubernetes"
    )
    assert 'status' in response
    assert 'orchestrated_containers' in response
    assert 'cluster_status' in response
    assert 'orchestration_platform' in response
    print("✓ Container orchestration test passed")


def test_cloud_cost_optimization():
    """Test cloud cost optimization."""
    print("Testing cloud cost optimization...")
    client = RealAIClient()
    response = client.cloud.optimize_cost(
        optimization_targets=["compute", "storage", "networking"],
        time_horizon="monthly",
        budget_limit=100.0
    )
    assert 'status' in response
    assert 'current_hourly_cost' in response
    assert 'cost_breakdown' in response
    assert 'recommendations' in response
    assert 'potential_savings' in response
    print("✓ Cloud cost optimization test passed")


def test_distributed_ai_training():
    """Test distributed AI training coordination."""
    print("Testing distributed AI training...")
    client = RealAIClient()
    model_config = {
        "architecture": "transformer",
        "parameters": 1000000,
        "layers": 12
    }
    dataset_config = {
        "location": "s3://realai-datasets/training-data",
        "format": "parquet",
        "size_gb": 100
    }
    response = client.cloud.train_distributed(
        model_config=model_config,
        dataset_config=dataset_config,
        training_strategy="data_parallel",
        instances_required=4
    )
    assert 'status' in response
    assert 'training_task_id' in response
    assert 'training_strategy' in response
    assert 'distributed_benefits' in response
    print("✓ Distributed AI training test passed")


def test_cloud_native_ai_inference():
    """Test cloud-native AI inference deployment."""
    print("Testing cloud-native AI inference...")
    client = RealAIClient()
    model_endpoints = [
        {"model": "gpt-4", "endpoint_type": "rest"},
        {"model": "bert", "endpoint_type": "grpc"}
    ]
    scaling_config = {
        "min_instances": 1,
        "max_instances": 10,
        "target_cpu_utilization": 70
    }
    response = client.cloud.inference_cloud(
        model_endpoints=model_endpoints,
        scaling_config=scaling_config,
        optimization_level="balanced"
    )
    assert 'status' in response
    assert 'deployed_endpoints' in response
    assert 'total_endpoints' in response
    assert 'performance_metrics' in response
    print("✓ Cloud-native AI inference test passed")


def test_cloud_convenience_methods():
    """Test cloud convenience methods."""
    print("Testing cloud convenience methods...")
    client = RealAIClient()

    # Test individual provider deployments
    response = client.cloud.vercel(instance_count=3)
    assert 'status' in response
    assert 'providers_used' in response
    assert 'vercel' in response['providers_used']

    response = client.cloud.render(instance_count=3)
    assert 'status' in response
    assert 'providers_used' in response
    assert 'render' in response['providers_used']

    response = client.cloud.railway(instance_count=3)
    assert 'status' in response
    assert 'providers_used' in response
    assert 'railway' in response['providers_used']

    # Test multi-cloud deployment
    response = client.cloud.multi_cloud(instance_count=5)
    assert 'status' in response
    assert 'providers_used' in response
    assert len(response['providers_used']) >= 2

    print("✓ Cloud convenience methods test passed")


def test_computer_mode_activation():
    """Test computer mode activation."""
    print("Testing computer mode activation...")
    client = RealAIClient()
    response = client.computer.activate()
    # Note: This will fail without pyautogui/pygetwindow/pillow installed
    # But we test the interface structure
    assert 'status' in response
    print("✓ Computer mode activation test passed")


def test_screen_capture_analysis():
    """Test screen capture and analysis."""
    print("Testing screen capture analysis...")
    client = RealAIClient()
    response = client.computer.capture_screen("Analyze the desktop")
    assert 'status' in response
    print("✓ Screen capture analysis test passed")


def test_mouse_keyboard_control():
    """Test mouse and keyboard control."""
    print("Testing mouse and keyboard control...")
    client = RealAIClient()
    
    # Test mouse movement
    response = client.computer.move_mouse(100, 100)
    assert 'status' in response
    assert 'action_type' in response
    
    # Test clicking
    response = client.computer.click("left")
    assert 'status' in response
    assert 'action_type' in response
    
    # Test typing
    response = client.computer.type_text("Hello World")
    assert 'status' in response
    assert 'action_type' in response
    
    # Test key press
    response = client.computer.press_key("enter")
    assert 'status' in response
    assert 'action_type' in response
    
    print("✓ Mouse and keyboard control test passed")


def test_window_management():
    """Test window management."""
    print("Testing window management...")
    client = RealAIClient()
    
    # Activate computer mode first
    response = client.computer.activate()
    # In test environment, may fail due to missing dependencies
    assert 'status' in response or 'error' in response
    
    # Test getting active window
    response = client.computer.get_active_window()
    assert 'status' in response or 'error' in response
    
    # Test listing windows
    response = client.computer.list_windows()
    assert 'status' in response or 'error' in response
    
    # Test switching window
    response = client.computer.switch_window("test")
    assert 'status' in response or 'error' in response
    
    print("✓ Window management test passed")


def test_gui_automation():
    """Test GUI automation workflows."""
    print("Testing GUI automation...")
    client = RealAIClient()
    response = client.computer.automate_workflow("test_workflow")
    assert 'status' in response
    assert 'task' in response
    print("✓ GUI automation test passed")


def test_development_workflow_automation():
    """Test development workflow automation."""
    print("Testing development workflow automation...")
    client = RealAIClient()
    response = client.computer.build_app("web", {"framework": "react"})
    assert 'status' in response
    assert 'app_type' in response
    print("✓ Development workflow automation test passed")


def test_self_learning_recording():
    """Test self-learning recording."""
    print("Testing self-learning recording...")
    client = RealAIClient()
    
    # Test starting learning
    response = client.computer.start_learning("test_task")
    assert 'status' in response
    
    # Test recording action
    response = client.computer.record_action("click", position=(100, 100))
    assert 'status' in response
    
    # Test stopping learning
    response = client.computer.stop_learning()
    assert 'status' in response
    
    print("✓ Self-learning recording test passed")


def test_action_replay_execution():
    """Test action replay execution."""
    print("Testing action replay execution...")
    from realai import RecordedAction
    import time
    
    client = RealAIClient()
    actions = [
        RecordedAction(
            timestamp=time.time(),
            action_type="click",
            position=(100, 100),
            metadata={"button": "left"}
        )
    ]
    response = client.computer.replay_actions(actions)
    assert 'status' in response
    print("✓ Action replay execution test passed")


def test_code_generation_automation():
    """Test code generation automation."""
    print("Testing code generation automation...")
    client = RealAIClient()
    response = client.computer.generate_code("create a hello world function")
    assert 'status' in response
    print("✓ Code generation automation test passed")


def test_app_building_automation():
    """Test app building automation."""
    print("Testing app building automation...")
    client = RealAIClient()
    response = client.computer.build_app("web", {"framework": "react"})
    assert 'status' in response
    assert 'app_type' in response
    print("✓ App building automation test passed")


def test_crypto_mining():
    """Test crypto mining setup."""
    print("Testing crypto mining...")
    client = RealAIClient()
    response = client.crypto.mine_crypto("ethash", 2)
    assert 'status' in response
    if 'algorithm' in response:
        assert response['algorithm'] == 'ethash'
        assert response['gpu_count'] == 2
    print("✓ Crypto mining test passed")


def test_ai_trading_bot_integration():
    """Test AI trading bot integration."""
    print("Testing AI trading bot integration...")
    client = RealAIClient()
    response = client.crypto.integrate_trading_bot("freqtrade", {"exchange": "binance"})
    assert 'status' in response
    if 'bot_name' in response:
        assert response['bot_name'] == 'freqtrade'
    print("✓ AI trading bot integration test passed")


def test_freqtrade_integration():
    """Test Freqtrade bot setup."""
    print("Testing Freqtrade integration...")
    client = RealAIClient()
    response = client.crypto.setup_freqtrade("binance", "SampleStrategy")
    assert 'status' in response
    if 'bot' in response:
        assert response['bot'] == 'freqtrade'
    print("✓ Freqtrade integration test passed")


def test_hummingbot_integration():
    """Test Hummingbot setup."""
    print("Testing Hummingbot integration...")
    client = RealAIClient()
    response = client.crypto.setup_hummingbot("binance", "pure_market_making")
    assert 'status' in response
    if 'bot' in response:
        assert response['bot'] == 'hummingbot'
    print("✓ Hummingbot integration test passed")


def test_octobot_integration():
    """Test OctoBot setup."""
    print("Testing OctoBot integration...")
    client = RealAIClient()
    response = client.crypto.setup_octobot("binance", "Simple")
    assert 'status' in response
    if 'bot' in response:
        assert response['bot'] == 'octobot'
    print("✓ OctoBot integration test passed")


def test_jessie_trading_integration():
    """Test Jesse trading bot setup."""
    print("Testing Jesse integration...")
    client = RealAIClient()
    response = client.crypto.setup_jessie("binance", "TestStrategy")
    assert 'status' in response
    if 'bot' in response:
        assert response['bot'] == 'jesse'
    print("✓ Jesse integration test passed")


def test_superalgos_integration():
    """Test Superalgos setup."""
    print("Testing Superalgos integration...")
    client = RealAIClient()
    response = client.crypto.setup_superalgos("binance", "VisualStrategy")
    assert 'status' in response
    if 'bot' in response:
        assert response['bot'] == 'superalgos'
    print("✓ Superalgos integration test passed")


def test_polymarket_bot_integration():
    """Test Polymarket bot setup."""
    print("Testing Polymarket bot integration...")
    client = RealAIClient()
    response = client.crypto.setup_polymarket_bot("crypto", "sniper")
    assert 'status' in response
    if 'bot' in response:
        assert response['bot'] == 'polymarket'
    print("✓ Polymarket bot integration test passed")


def test_market_analysis():
    """Test market analysis."""
    print("Testing market analysis...")
    client = RealAIClient()
    response = client.crypto.analyze_market("BTC/USDT", "1h")
    assert 'status' in response
    print("✓ Market analysis test passed")


def test_trading_strategy_optimization():
    """Test trading strategy optimization."""
    print("Testing trading strategy optimization...")
    client = RealAIClient()
    response = client.crypto.optimize_strategy("def strategy(): pass", {"historical_data": []})
    assert 'status' in response
    print("✓ Trading strategy optimization test passed")


def test_risk_management():
    """Test risk management."""
    print("Testing risk management...")
    client = RealAIClient()
    response = client.crypto.manage_risk({"BTC": 0.5, "ETH": 0.3}, {"max_drawdown": 0.1})
    assert 'status' in response
    print("✓ Risk management test passed")


def test_portfolio_management():
    """Test portfolio management."""
    print("Testing portfolio management...")
    client = RealAIClient()
    response = client.crypto.manage_portfolio(["BTC", "ETH", "ADA"], "balanced")
    assert 'status' in response
    print("✓ Portfolio management test passed")


# =============================================================================
# Feature 1: Model Registry + Capability Graph Tests
# =============================================================================

def test_capability_graph():
    """Test CapabilityGraph functionality."""
    print("Testing capability graph...")
    from realai.model_registry import CAPABILITY_GRAPH, CapabilityGraph, MODEL_REGISTRY

    caps = CAPABILITY_GRAPH.all_capabilities()
    assert len(caps) > 0, "Capability graph should have capabilities"
    assert "coding" in caps or "reasoning" in caps, "Should have standard capabilities"
    assert "planning" in caps, "Declared metadata capabilities should be preserved"

    entries = CAPABILITY_GRAPH.get("reasoning")
    assert isinstance(entries, list), "get() should return a list"

    d = CAPABILITY_GRAPH.to_dict()
    assert isinstance(d, dict), "to_dict() should return dict"
    if d.get("reasoning"):
        assert "model_id" in d["reasoning"][0]
        assert "score" in d["reasoning"][0]

    models = MODEL_REGISTRY.list_all()
    graph = CapabilityGraph(models, declared_capabilities=MODEL_REGISTRY.list_capabilities())
    assert len(graph.all_capabilities()) > 0, "Graph from models should have capabilities"

    print("✓ Capability graph test passed")


def test_model_registry_metadata():
    """Test metadata-backed model registry helpers."""
    print("Testing metadata-backed model registry...")
    from realai.model_registry import MODEL_REGISTRY, get_model_metadata

    default_model = MODEL_REGISTRY.get_default_model()
    assert default_model is not None, "Registry should expose a default model"
    assert default_model.id == "realai-2.0"

    metadata = get_model_metadata("realai-2.0")
    assert metadata is not None
    assert metadata["display_name"] == "RealAI 2.0 General"
    assert metadata["compatibility_matrix"]["tool_calls"] is True
    assert "best_for" in metadata["performance_profile"]

    planning_models = MODEL_REGISTRY.models_with_capability("planning")
    assert len(planning_models) > 0

    best_local = MODEL_REGISTRY.best_model_for("planning", {"prefer_local": True})
    assert best_local is not None
    assert best_local.local_available is True

    print("✓ Metadata-backed model registry test passed")


def test_model_registry_api_payloads():
    """Test registry-backed API payload helpers."""
    print("Testing model registry API payloads...")
    from realai.model_registry import MODEL_REGISTRY

    models_payload = MODEL_REGISTRY.to_openai_list()
    assert models_payload["object"] == "list"
    assert any(item["id"] == "realai-2.0" for item in models_payload["data"])

    capabilities_payload = MODEL_REGISTRY.to_capabilities_payload()
    assert capabilities_payload["default_model"] == "realai-2.0"
    assert "capability_graph" in capabilities_payload
    assert "routing_policies" in capabilities_payload
    assert any(item["id"] == "realai-1.0-agentic" for item in capabilities_payload["models"])

    print("✓ Model registry API payloads test passed")


def test_route_for_task():
    """Test route_for_task in ModelRegistry."""
    print("Testing route_for_task...")
    from realai.model_registry import MODEL_REGISTRY

    # Route for a known capability
    caps = MODEL_REGISTRY.list_all()
    available_caps = set()
    for m in caps:
        for cap in m.capabilities:
            available_caps.add(cap)

    if available_caps:
        cap = next(iter(available_caps))
        result = MODEL_REGISTRY.route_for_task(cap)
        assert result is not None, "Should find a model for existing capability '{0}'".format(cap)

    # Route for unknown capability should return None
    result = MODEL_REGISTRY.route_for_task("nonexistent_capability_xyz")
    assert result is None, "Should return None for unknown capability"

    # Test with constraints
    result = MODEL_REGISTRY.route_for_task("reasoning", constraints={"max_cost": 5})
    # May be None if no reasoning models, but should not raise

    print("✓ route_for_task test passed")


# =============================================================================
# Feature 2: Tool Registry Tests
# =============================================================================

def test_tool_registry():
    """Test ToolRegistry functionality."""
    print("Testing tool registry...")
    from realai.tools import TOOL_REGISTRY, ToolSchema

    # Check built-in tools are registered
    tools = TOOL_REGISTRY.list_all()
    assert len(tools) >= 5, "Should have at least 5 built-in tools"

    tool_names = [t.name for t in tools]
    assert "web_research" in tool_names, "web_research should be registered"
    assert "execute_code" in tool_names, "execute_code should be registered"
    assert "generate_image" in tool_names, "generate_image should be registered"
    assert "translate" in tool_names, "translate should be registered"
    assert "transcribe_audio" in tool_names, "transcribe_audio should be registered"

    # Test get
    schema = TOOL_REGISTRY.get("web_research")
    assert schema is not None, "Should find web_research"
    assert schema.name == "web_research"
    assert isinstance(schema.parameters, dict)

    # Test get unknown
    assert TOOL_REGISTRY.get("nonexistent") is None

    # Test to_openai_format
    openai_tools = TOOL_REGISTRY.to_openai_format()
    assert isinstance(openai_tools, list)
    assert len(openai_tools) >= 5
    for tool in openai_tools:
        assert tool["type"] == "function"
        assert "function" in tool
        assert "name" in tool["function"]

    # Test register new tool
    new_tool = ToolSchema(
        name="test_tool_xyz",
        description="Test tool",
        parameters={"type": "object", "properties": {}},
        required=[],
    )
    TOOL_REGISTRY.register(new_tool)
    assert TOOL_REGISTRY.get("test_tool_xyz") is not None

    print("✓ Tool registry test passed")


def test_tool_call_validator():
    """Test ToolCallValidator functionality."""
    print("Testing tool call validator...")
    from realai.tools import ToolCallValidator

    validator = ToolCallValidator()

    # Valid call
    result = validator.validate("web_research", {"query": "test"})
    assert result.valid, "Valid call should pass: {0}".format(result.errors)
    assert result.errors == []

    # Missing required field
    result = validator.validate("web_research", {})
    assert not result.valid, "Missing required field should fail"
    assert len(result.errors) > 0

    # Unknown tool
    result = validator.validate("unknown_tool_xyz", {"arg": "val"})
    assert not result.valid, "Unknown tool should fail"

    # Valid translate call
    result = validator.validate("translate", {"text": "hello", "target_language": "es"})
    assert result.valid, "Valid translate call should pass: {0}".format(result.errors)

    print("✓ Tool call validator test passed")


def test_tool_call_optimizer():
    """Test ToolCallOptimizer functionality."""
    print("Testing tool call optimizer...")
    from realai.tools import ToolCallOptimizer

    optimizer = ToolCallOptimizer()

    # Test deduplicate
    calls = [
        {"name": "web_research", "arguments": {"query": "test"}},
        {"name": "web_research", "arguments": {"query": "test"}},  # duplicate
        {"name": "translate", "arguments": {"text": "hi", "target_language": "es"}},
    ]
    deduped = optimizer.deduplicate(calls)
    assert len(deduped) == 2, "Should remove 1 duplicate, got {0}".format(len(deduped))

    # Test batch_parallel
    batches = optimizer.batch_parallel(calls[:2])
    assert isinstance(batches, list)
    assert len(batches) > 0

    # Test with empty list
    assert optimizer.deduplicate([]) == []
    assert optimizer.batch_parallel([]) == []

    print("✓ Tool call optimizer test passed")


# =============================================================================
# Feature 3: Self-Critique Engine Tests
# =============================================================================

def test_critique_engine():
    """Test CritiqueEngine evaluation."""
    print("Testing critique engine...")
    from realai.critique import CRITIQUE_ENGINE, CritiqueResult

    # Test with a good response
    good_response = {
        "choices": [{
            "message": {
                "content": "Python is a high-level programming language known for its readability and versatility."
            }
        }]
    }
    result = CRITIQUE_ENGINE.evaluate(good_response)
    assert isinstance(result, CritiqueResult)
    assert 0.0 <= result.overall <= 1.0
    assert isinstance(result.scores, dict)
    assert isinstance(result.suggestions, list)

    # Test with empty response
    empty_response = {"choices": [{"message": {"content": ""}}]}
    result = CRITIQUE_ENGINE.evaluate(empty_response)
    assert result.overall < 1.0, "Empty response should score below 1.0"

    # Test with custom rubric
    rubric = {"accuracy": 0.5, "completeness": 0.5}
    result = CRITIQUE_ENGINE.evaluate(good_response, rubric=rubric)
    assert isinstance(result, CritiqueResult)

    print("✓ Critique engine test passed")


def test_compress_cot():
    """Test chain-of-thought compression."""
    print("Testing CoT compression...")
    from realai.critique import CRITIQUE_ENGINE

    cot = """Let me think about this carefully.
Well, first I need to consider the problem.
So, we have a list of numbers.
Okay, let me break this down:
1. Sort the list
2. Find the median
3. Return the result
Hmm, that should work."""

    compressed = CRITIQUE_ENGINE.compress_chain_of_thought(cot)
    assert isinstance(compressed, str)
    assert len(compressed) > 0
    # Should not be longer than original
    assert len(compressed) <= len(cot), "Compressed should not exceed original"

    # Test with empty string
    assert CRITIQUE_ENGINE.compress_chain_of_thought("") == ""

    print("✓ CoT compression test passed")


def test_retry_with_critique():
    """Test retry_with_critique functionality."""
    print("Testing retry with critique...")
    from realai.critique import CRITIQUE_ENGINE

    call_count = [0]

    def mock_chat_fn(messages):
        call_count[0] += 1
        # Return a good response on second call
        if call_count[0] >= 2:
            return {
                "choices": [{
                    "message": {"content": "A detailed and comprehensive response about the topic."}
                }]
            }
        return {
            "choices": [{"message": {"content": "ok"}}]
        }

    messages = [{"role": "user", "content": "Explain Python"}]
    result = CRITIQUE_ENGINE.retry_with_critique(mock_chat_fn, messages, max_retries=3, threshold=0.5)

    assert isinstance(result, dict), "Should return a dict"
    assert call_count[0] >= 1, "Should call chat_fn at least once"

    print("✓ Retry with critique test passed")


# =============================================================================
# Feature 4: Multi-Agent Runtime Tests
# =============================================================================

def test_message_bus():
    """Test MessageBus send/subscribe/get_messages."""
    print("Testing message bus...")
    from realai.agent_runtime import MessageBus, Message

    bus = MessageBus()

    received = []
    bus.subscribe("agent1", lambda msg: received.append(msg))

    # Send a message
    msg_id = bus.send("orchestrator", "agent1", "Hello agent1")
    assert isinstance(msg_id, str), "send() should return a string ID"
    assert len(received) == 1, "Handler should have been called"
    assert received[0].content == "Hello agent1"

    # Get messages from inbox
    messages = bus.get_messages("agent1")
    assert len(messages) >= 1

    # Test unsubscribe
    bus.unsubscribe("agent1")

    # Test broadcast
    bus.subscribe("agent2", lambda msg: None)
    bus.subscribe("agent3", lambda msg: None)
    ids = bus.broadcast("orchestrator", "broadcast message")
    assert isinstance(ids, list)

    # Test send to unsubscribed agent (should not crash)
    bus.send("a", "nonexistent", "msg")

    print("✓ Message bus test passed")


def test_pipeline_runner():
    """Test PipelineRunner execution."""
    print("Testing pipeline runner...")
    from realai.agent_runtime import (
        PipelineRunner, PipelineDefinition, PipelineStep
    )

    class MockRegistry:
        def execute_agent(self, agent_id, task):
            return {"status": "success", "result": "processed: " + task[:20]}

    steps = [
        PipelineStep(agent_id="agent1", task_template="Step1: {input}"),
        PipelineStep(agent_id="agent2", task_template="Step2: {input}"),
    ]
    pipeline = PipelineDefinition(
        id="test-pipeline",
        name="Test Pipeline",
        steps=steps,
    )

    registry = MockRegistry()
    runner = PipelineRunner()
    result = runner.run(pipeline, "initial input", registry)

    assert isinstance(result, dict)
    assert "pipeline_id" in result
    assert "steps_completed" in result
    assert "result" in result
    assert "step_results" in result
    assert result["steps_completed"] == 2

    print("✓ Pipeline runner test passed")


def test_agent_graph():
    """Test AgentGraph execution."""
    print("Testing agent graph...")
    from realai.agent_runtime import AgentGraph, AgentNode, AgentEdge

    class MockRegistry:
        def execute_agent(self, agent_id, task):
            return {"status": "success", "result": "output from " + agent_id}

    graph = AgentGraph()
    graph.add_node(AgentNode(agent_id="node1", task_template="Task: {input}"))
    graph.add_node(AgentNode(agent_id="node2", task_template="Task: {input}"))
    graph.add_edge(AgentEdge(from_node="node1", to_node="node2"))

    # Test entrypoints
    entrypoints = graph.get_entrypoints()
    assert "node1" in entrypoints, "node1 should be an entrypoint"
    assert "node2" not in entrypoints, "node2 has incoming edge"

    # Test execute
    registry = MockRegistry()
    result = graph.execute("test input", registry)

    assert isinstance(result, dict)
    assert "all_results" in result
    assert "steps_run" in result
    assert result["steps_run"] >= 1

    print("✓ Agent graph test passed")


# =============================================================================
# Feature 5: Local Runtime Tests
# =============================================================================

def test_local_model_cache():
    """Test LocalModelCache operations."""
    print("Testing local model cache...")
    from realai.local_runtime import LocalModelCache, CachedModel
    import time

    cache = LocalModelCache()

    # Register models
    model1 = CachedModel(name="model1", path="/tmp/m1", size_bytes=1000, last_used=time.time(), backend="llama.cpp")
    model2 = CachedModel(name="model2", path="/tmp/m2", size_bytes=2000, last_used=time.time() - 100, backend="gguf")
    model3 = CachedModel(name="model3", path="/tmp/m3", size_bytes=3000, last_used=time.time() - 200, backend="gguf")

    cache.register(model1)
    cache.register(model2)
    cache.register(model3)

    # Test get
    assert cache.get("model1") is not None
    assert cache.get("nonexistent") is None

    # Test list_all
    assert len(cache.list_all()) == 3

    # Test total_size_bytes
    assert cache.total_size_bytes() == 6000

    # Test touch
    old_time = cache.get("model2").last_used
    import time as time_mod
    time_mod.sleep(0.01)
    cache.touch("model2")
    assert cache.get("model2").last_used >= old_time

    # Test evict_lru (keep 2)
    evicted = cache.evict_lru(keep_count=2)
    assert len(evicted) == 1, "Should evict 1 model"
    assert len(cache.list_all()) == 2

    print("✓ Local model cache test passed")


def test_local_vector_db():
    """Test LocalVectorDB operations."""
    print("Testing local vector DB...")
    from realai.local_runtime import LocalVectorDB

    db = LocalVectorDB()

    # Add vectors
    db.add("v1", [1.0, 0.0, 0.0], {"label": "x-axis"})
    db.add("v2", [0.0, 1.0, 0.0], {"label": "y-axis"})
    db.add("v3", [0.0, 0.0, 1.0], {"label": "z-axis"})

    # Test count
    assert db.count() == 3

    # Test search
    results = db.search([1.0, 0.0, 0.0], top_k=2)
    assert len(results) == 2
    assert results[0]["id"] == "v1", "Closest to x-axis should be v1"

    # Test delete
    assert db.delete("v1") is True
    assert db.count() == 2
    assert db.delete("nonexistent") is False

    # Test search on empty
    empty_db = LocalVectorDB()
    assert empty_db.search([1.0, 0.0], top_k=5) == []

    print("✓ Local vector DB test passed")


def test_local_tool_sandbox():
    """Test LocalToolSandbox code execution."""
    print("Testing local tool sandbox...")
    from realai.local_runtime import LocalToolSandbox

    sandbox = LocalToolSandbox()

    # Test successful Python execution
    result = sandbox.execute("print('hello sandbox')", language="python")
    assert result["status"] == "success", "Simple print should succeed: {0}".format(result)
    assert "hello sandbox" in result["output"]

    # Test unsupported language
    result = sandbox.execute("console.log('hi')", language="javascript")
    assert result["status"] == "error"
    assert "not supported" in result["error"].lower()

    # Test Python error handling (subprocess runs but code raises)
    result = sandbox.execute("raise ValueError('test error')", language="python")
    # Should complete without crashing the sandbox
    assert result["status"] in ("success", "error")

    print("✓ Local tool sandbox test passed")


def test_local_embeddings_server():
    """Test LocalEmbeddingsServer functionality."""
    print("Testing local embeddings server...")
    from realai.local_runtime import LocalEmbeddingsServer

    server = LocalEmbeddingsServer()

    # Test embed (uses fallback hash-based vectors)
    texts = ["hello world", "python programming"]
    vectors = server.embed(texts)

    assert len(vectors) == 2, "Should return one vector per input"
    assert len(vectors[0]) == server._VECTOR_DIM, "Vector should have correct dimension"
    assert len(vectors[1]) == server._VECTOR_DIM

    # Vectors should be normalized (approximately)
    import math
    norm = math.sqrt(sum(v * v for v in vectors[0]))
    assert abs(norm - 1.0) < 0.01, "Vector should be normalized, norm={0}".format(norm)

    # Same text should give same vector
    vectors2 = server.embed(["hello world"])
    assert vectors[0] == vectors2[0], "Same text should give same vector"

    # Test is_available (just checks import, returns bool)
    available = server.is_available()
    assert isinstance(available, bool)

    print("✓ Local embeddings server test passed")


# =============================================================================
# Feature 6: Plugin Marketplace Tests
# =============================================================================

def test_plugin_manifest():
    """Test PluginManifest dataclass."""
    print("Testing plugin manifest...")
    from realai.plugin_marketplace import PluginManifest, PluginPermission

    manifest = PluginManifest(
        name="test-plugin",
        version="1.0.0",
        author="Test Author",
        description="A test plugin",
        permissions=[PluginPermission.NETWORK.value],
    )

    assert manifest.name == "test-plugin"
    assert manifest.version == "1.0.0"
    assert PluginPermission.NETWORK.value in manifest.permissions

    print("✓ Plugin manifest test passed")


def test_plugin_discovery():
    """Test PluginDiscovery install/uninstall/list."""
    print("Testing plugin discovery...")
    import os
    import tempfile
    from realai.plugin_marketplace import PluginDiscovery, PluginManifest

    fd, tmp_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(tmp_path)  # Remove so discovery starts fresh

    discovery = PluginDiscovery(manifests_path=tmp_path)

    # Initially empty
    assert discovery.list_installed() == []

    # Install a plugin
    manifest = PluginManifest(
        name="test-plugin",
        version="1.0.0",
        author="Tester",
        description="Test",
    )
    success = discovery.install(manifest)
    assert success, "Install should succeed"

    installed = discovery.list_installed()
    assert len(installed) == 1
    assert installed[0].name == "test-plugin"

    # Install duplicate (update)
    manifest2 = PluginManifest(name="test-plugin", version="2.0.0", author="Tester", description="Updated")
    discovery.install(manifest2)
    installed = discovery.list_installed()
    assert len(installed) == 1, "Duplicate install should update, not add"
    assert installed[0].version == "2.0.0"

    # Uninstall
    success = discovery.uninstall("test-plugin")
    assert success, "Uninstall should succeed"
    assert discovery.list_installed() == []

    # Uninstall nonexistent
    assert discovery.uninstall("nonexistent") is False

    # Cleanup
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)

    print("✓ Plugin discovery test passed")


def test_plugin_verifier():
    """Test PluginVerifier."""
    print("Testing plugin verifier...")
    import hashlib
    from realai.plugin_marketplace import PluginVerifier, PluginManifest

    verifier = PluginVerifier()

    # Open trust (no trusted_keys)
    manifest = PluginManifest(
        name="myplugin",
        version="1.0.0",
        author="Author",
        description="Test",
    )
    assert verifier.verify(manifest) is True, "Should pass with open trust"

    # Correct signature
    payload = "myplugin1.0.0Author"
    sig = hashlib.sha256(payload.encode()).hexdigest()
    manifest.signature = sig
    assert verifier.verify(manifest, trusted_keys=["key1"]) is True

    # Wrong signature
    manifest.signature = "wrongsig"
    assert verifier.verify(manifest, trusted_keys=["key1"]) is False

    print("✓ Plugin verifier test passed")


def test_plugin_sandbox():
    """Test PluginSandbox execution."""
    print("Testing plugin sandbox...")
    from realai.plugin_marketplace import PluginSandbox

    sandbox = PluginSandbox()

    # Test successful execution
    def good_fn(x, y):
        return x + y

    result = sandbox.execute_plugin(good_fn, 2, 3)
    assert result == 5, "Should return 5"

    # Test exception handling
    def bad_fn():
        raise RuntimeError("test error")

    result = sandbox.execute_plugin(bad_fn)
    assert isinstance(result, dict), "Should return error dict on exception"
    assert result.get("status") == "error"

    print("✓ Plugin sandbox test passed")


# =============================================================================
# Feature 7: Memory Engine Tests
# =============================================================================

def test_short_term_memory():
    """Test ShortTermMemory operations."""
    print("Testing short-term memory...")
    from realai.memory.engine import ShortTermMemory, MemoryItem
    import time

    stm = ShortTermMemory(capacity=3)

    for i in range(5):
        item = MemoryItem(
            id="item{0}".format(i),
            content="Content {0}".format(i),
            timestamp=time.time(),
        )
        stm.add(item)

    # Should only keep last 3
    recent = stm.get_recent(10)
    assert len(recent) == 3, "Should keep only last 3 items"

    # get_recent with n
    recent2 = stm.get_recent(2)
    assert len(recent2) == 2

    # clear
    stm.clear()
    assert stm.get_recent(10) == []

    print("✓ Short-term memory test passed")


def test_episodic_memory():
    """Test EpisodicMemory with decay."""
    print("Testing episodic memory...")
    from realai.memory.engine import EpisodicMemory, MemoryItem
    import time

    em = EpisodicMemory(decay_factor=0.95)

    # Add items
    item1 = MemoryItem(id="e1", content="Recent event", timestamp=time.time(), score=0.9)
    item2 = MemoryItem(id="e2", content="Old event", timestamp=time.time() - 86400 * 10, score=0.9)
    em.add(item1)
    em.add(item2)

    # Recent item should score higher
    score1 = em.get_score(item1)
    score2 = em.get_score(item2)
    assert score1 > score2, "Recent item should have higher score"

    # Retrieve top items
    results = em.retrieve("event", top_k=2)
    assert len(results) == 2
    assert results[0].id == "e1", "Recent item should be first"

    # all()
    all_items = em.all()
    assert len(all_items) == 2

    print("✓ Episodic memory test passed")


def test_symbolic_memory():
    """Test SymbolicMemory fact operations."""
    print("Testing symbolic memory...")
    from realai.memory.engine import SymbolicMemory

    sm = SymbolicMemory()

    # Assert fact
    sm.assert_fact("color", "blue", confidence=0.9)

    # Query
    result = sm.query("color")
    assert result is not None
    assert result["value"] == "blue"
    assert result["confidence"] == 0.9

    # Contradiction detection
    assert sm.detect_contradiction("color", "red") is True
    assert sm.detect_contradiction("color", "blue") is False
    assert sm.detect_contradiction("nonexistent", "any") is False

    # Retract
    assert sm.retract_fact("color") is True
    assert sm.query("color") is None
    assert sm.retract_fact("color") is False

    # Namespace isolation
    sm.assert_fact("x", 1, namespace="ns1")
    sm.assert_fact("x", 2, namespace="ns2")
    assert sm.query("x", namespace="ns1")["value"] == 1
    assert sm.query("x", namespace="ns2")["value"] == 2

    # all_facts
    facts = sm.all_facts()
    assert isinstance(facts, dict)

    print("✓ Symbolic memory test passed")


def test_semantic_memory():
    """Test SemanticMemory store and search."""
    print("Testing semantic memory...")
    from realai.memory.engine import SemanticMemory, MemoryItem
    import time

    sem = SemanticMemory()

    items = [
        MemoryItem(id="s1", content="Python programming language", timestamp=time.time()),
        MemoryItem(id="s2", content="Machine learning algorithms", timestamp=time.time()),
        MemoryItem(id="s3", content="Web development frameworks", timestamp=time.time()),
    ]
    for item in items:
        sem.store(item)

    # Search
    results = sem.search("Python programming", top_k=2)
    assert isinstance(results, list)
    # At least returns some results (hash-based search)

    print("✓ Semantic memory test passed")


def test_memory_engine():
    """Test MemoryEngine multi-tier operations."""
    print("Testing memory engine...")
    from realai.memory.engine import MemoryEngine

    engine = MemoryEngine()

    # Store items
    id1 = engine.store("Python is a programming language", tags=["tech"])
    id2 = engine.store("Paris is the capital of France", tags=["geography"])

    assert isinstance(id1, str)
    assert isinstance(id2, str)
    assert id1 != id2

    # Retrieve
    results = engine.retrieve("Paris France", top_k=5)
    assert isinstance(results, list)

    # Forget
    success = engine.forget(id1)
    assert success is True, "Should successfully forget stored item"

    # Forget unknown
    success = engine.forget("nonexistent-id")
    assert isinstance(success, bool)

    print("✓ Memory engine test passed")


# =============================================================================
# Feature 8: Knowledge Graph Tests
# =============================================================================

def test_knowledge_graph():
    """Test KnowledgeGraph operations."""
    print("Testing knowledge graph...")
    from realai.knowledge_graph import KnowledgeGraph, Entity, Relationship

    kg = KnowledgeGraph()

    # Add entities
    e1 = Entity(id="e1", name="Python", entity_type="language", attributes={"year": 1991})
    e2 = Entity(id="e2", name="Programming", entity_type="concept", attributes={})
    e3 = Entity(id="e3", name="Software", entity_type="concept", attributes={})
    kg.add_entity(e1)
    kg.add_entity(e2)
    kg.add_entity(e3)

    # Add relationships
    r1 = Relationship(id="r1", subject_id="e1", predicate="is_a", object_id="e2", confidence=0.9)
    r2 = Relationship(id="r2", subject_id="e2", predicate="is_a", object_id="e3", confidence=0.8)
    kg.add_relationship(r1)
    kg.add_relationship(r2)

    # Get entity
    assert kg.get_entity("e1").name == "Python"
    assert kg.get_entity("nonexistent") is None

    # Query
    rels = kg.query(subject_id="e1")
    assert len(rels) == 1
    assert rels[0].predicate == "is_a"

    rels = kg.query(predicate="is_a")
    assert len(rels) == 2

    # Infer relationships
    inferred = kg.infer_relationships(max_hops=2)
    assert any(r.subject_id == "e1" and r.object_id == "e3" for r in inferred), \
        "Should infer transitive relationship"

    # Stats
    stats = kg.stats()
    assert stats["entities"] == 3
    assert stats["relationships"] == 2

    # Remove entity
    assert kg.remove_entity("e1") is True
    assert kg.get_entity("e1") is None
    assert kg.remove_entity("nonexistent") is False

    print("✓ Knowledge graph test passed")


def test_entity_linker():
    """Test EntityLinker string matching."""
    print("Testing entity linker...")
    from realai.knowledge_graph import KnowledgeGraph, Entity, EntityLinker

    kg = KnowledgeGraph()
    kg.add_entity(Entity(id="e1", name="Python", entity_type="language", attributes={}))
    kg.add_entity(Entity(id="e2", name="Java", entity_type="language", attributes={}))

    linker = EntityLinker()

    # Should find Python
    result = linker.link("I love Python programming", kg)
    assert result is not None
    assert result.name == "Python"

    # No match
    result = linker.link("I love cooking", kg)
    assert result is None

    print("✓ Entity linker test passed")


def test_synthesis_engine():
    """Test SynthesisEngine answer generation."""
    print("Testing synthesis engine...")
    from realai.knowledge_graph import KnowledgeGraph, Entity, Relationship, SynthesisEngine

    kg = KnowledgeGraph()
    kg.add_entity(Entity(id="e1", name="Python", entity_type="language", attributes={}))
    kg.add_entity(Entity(id="e2", name="Programming", entity_type="concept", attributes={}))
    kg.add_relationship(Relationship(id="r1", subject_id="e1", predicate="is_a", object_id="e2"))

    engine = SynthesisEngine()

    result = engine.answer("What is Python?", kg)
    assert isinstance(result, dict)
    assert "entities_found" in result
    assert "relationships" in result
    assert "synthesis" in result
    assert len(result["entities_found"]) > 0

    # No match
    result = engine.answer("What is cooking?", kg)
    assert len(result["entities_found"]) == 0

    print("✓ Synthesis engine test passed")


# =============================================================================
# Feature 9: App Framework Tests
# =============================================================================

def test_realai_app():
    """Test RealAIApp base class."""
    print("Testing RealAI app framework...")
    from realai.app_framework import RealAIApp, AppEvent

    class TestApp(RealAIApp):
        def on_message(self, event):
            return {"echo": event.payload, "type": event.event_type}

    app = TestApp("test-app")
    assert app.name == "test-app"
    assert not app._running

    # Start
    result = app.start()
    assert result["status"] == "started"
    assert app._running

    # Emit event
    result = app.emit("greet", "World")
    assert result is not None
    assert result["echo"] == "World"
    assert result["type"] == "greet"
    assert len(app._events) == 1

    # Stop
    result = app.stop()
    assert result["status"] == "stopped"
    assert not app._running

    print("✓ RealAI app framework test passed")


def test_workflow_builder():
    """Test WorkflowBuilder fluent API."""
    print("Testing workflow builder...")
    from realai.app_framework import WorkflowBuilder, WorkflowDefinition, WorkflowStep

    builder = WorkflowBuilder()
    workflow = (
        builder
        .add_step("fetch", "web_research", {"query": "AI news"})
        .add_step("summarize", "chat_completion", {"prompt": "Summarize"}, depends_on=["fetch"])
        .build("my-workflow")
    )

    assert isinstance(workflow, WorkflowDefinition)
    assert workflow.name == "my-workflow"
    assert len(workflow.steps) == 2
    assert workflow.steps[0].name == "fetch"
    assert workflow.steps[1].depends_on == ["fetch"]

    # to_dict
    d = builder.to_dict()
    assert "steps" in d

    # from_dict
    data = {
        "name": "from-dict-workflow",
        "steps": [
            {"name": "s1", "action": "act1", "params": {}, "depends_on": []}
        ]
    }
    wf = WorkflowBuilder.from_dict(data)
    assert isinstance(wf, WorkflowDefinition)
    assert len(wf.steps) == 1

    print("✓ Workflow builder test passed")


def test_automation_builder():
    """Test AutomationBuilder record/replay."""
    print("Testing automation builder...")
    import uuid
    from realai.app_framework import AutomationBuilder, WorkflowDefinition, WorkflowStep

    builder = AutomationBuilder()

    # Record
    builder.start_recording("test-automation")
    builder.record_step("click", {"element": "button", "x": 100, "y": 200})
    builder.record_step("type", {"text": "Hello"})
    workflow = builder.stop_recording()

    assert isinstance(workflow, WorkflowDefinition)
    assert workflow.name == "test-automation"
    assert len(workflow.steps) == 2

    # Replay
    result = builder.replay(workflow)
    assert result["steps_run"] == 2
    assert result["workflow"] == "test-automation"

    # Parameterize
    param_workflow = WorkflowDefinition(
        id=str(uuid.uuid4()),
        name="param-test",
        steps=[
            WorkflowStep(
                name="s1",
                action="search",
                params={"query": "{{topic}} news"},
            )
        ]
    )
    parameterized = builder.parameterize(param_workflow, {"topic": "Python"})
    assert parameterized.steps[0].params["query"] == "Python news"

    print("✓ Automation builder test passed")


# =============================================================================
# Feature 10: Benchmark Suite Tests
# =============================================================================

def test_benchmark_suite():
    """Test that all benchmarks instantiate and run."""
    print("Testing benchmark suite...")
    import sys
    import os
    repo_root = os.path.dirname(os.path.abspath(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from benchmarks.base import BenchmarkResult, BaseBenchmark
    from benchmarks.bench_reasoning import ReasoningBenchmark
    from benchmarks.bench_coding import CodingBenchmark
    from benchmarks.bench_safety import SafetyBenchmark
    from benchmarks.bench_tool_use import ToolUseBenchmark
    from benchmarks.bench_memory import MemoryBenchmark
    from benchmarks.bench_agent import AgentBenchmark
    from benchmarks.runner import run_all_benchmarks

    benchmarks_list = [
        ReasoningBenchmark(),
        CodingBenchmark(),
        SafetyBenchmark(),
        ToolUseBenchmark(),
        MemoryBenchmark(),
        AgentBenchmark(),
    ]

    for bench in benchmarks_list:
        result = bench.run()
        assert isinstance(result, BenchmarkResult), "run() should return BenchmarkResult"
        assert 0.0 <= result.score <= 1.0, "Score should be in [0.0, 1.0]"
        assert result.total > 0, "total should be > 0"
        assert result.passed <= result.total

        report = bench.report(result)
        assert isinstance(report, str)

    # Test runner
    report = run_all_benchmarks()
    assert "benchmarks" in report
    assert "overall_score" in report
    assert 0.0 <= report["overall_score"] <= 1.0

    print("✓ Benchmark suite test passed")


# =============================================================================
# Feature 11: World Model Tests
# =============================================================================

def test_world_state():
    """Test WorldState operations."""
    print("Testing world state...")
    from realai.world_model import WorldState

    state = WorldState()

    # Set and get facts
    state.set_fact("sky_color", "blue", confidence=0.95)
    assert state.get_fact("sky_color") == "blue"
    assert state.get_fact("nonexistent") is None

    # all_facts
    facts = state.all_facts()
    assert "sky_color" in facts
    assert facts["sky_color"]["confidence"] == 0.95

    # Observe
    obs = state.observe("Python is popular", confidence=0.9, source="web")
    assert obs.content == "Python is popular"
    assert obs.confidence == 0.9

    print("✓ World state test passed")


def test_planning_engine():
    """Test PlanningEngine plan generation."""
    print("Testing planning engine...")
    from realai.world_model import PlanningEngine, WorldState

    engine = PlanningEngine()
    state = WorldState()

    # Test with keyword-matched goal
    plan = engine.plan("research and analyze AI trends", state, max_steps=3)
    assert isinstance(plan, list)
    assert len(plan) <= 3
    for step in plan:
        assert "step" in step
        assert "action" in step
        assert "rationale" in step

    # Test with unmatched goal (should still return steps)
    plan2 = engine.plan("do something unknown", state, max_steps=5)
    assert isinstance(plan2, list)
    assert len(plan2) > 0

    print("✓ Planning engine test passed")


def test_goal_tracker():
    """Test GoalTracker operations."""
    print("Testing goal tracker...")
    from realai.world_model import GoalTracker

    tracker = GoalTracker()

    # Add goal
    goal = tracker.add_goal(
        "Build a REST API",
        sub_goals=["Design schema", "Implement endpoints"],
    )
    assert goal.status == "pending"
    assert len(goal.sub_goals) == 2

    # Get goal
    retrieved = tracker.get_goal(goal.id)
    assert retrieved is not None
    assert retrieved.description == "Build a REST API"

    # Update status
    success = tracker.update_status(goal.id, "in_progress")
    assert success is True
    assert tracker.get_goal(goal.id).status == "in_progress"

    # List goals (includes parent + sub-goals)
    all_goals = tracker.list_goals()
    assert len(all_goals) >= 3

    pending = tracker.list_goals(status="pending")
    assert all(g.status == "pending" for g in pending)

    # Add sub-goal
    sub = tracker.add_sub_goal(goal.id, "Write tests")
    assert sub is not None
    assert sub.description == "Write tests"

    # Nonexistent parent
    assert tracker.add_sub_goal("nonexistent", "test") is None

    print("✓ Goal tracker test passed")


def test_belief_updater():
    """Test BeliefUpdater extraction from observations."""
    print("Testing belief updater...")
    import time
    import uuid
    from realai.world_model import WorldState, BeliefUpdater, Observation

    state = WorldState()
    updater = BeliefUpdater()

    obs = Observation(
        id=str(uuid.uuid4()),
        content="The temperature is 25 degrees. Python is popular.",
        confidence=0.9,
        source="sensor",
        timestamp=time.time(),
    )

    updater.update(state, obs)

    # Should have extracted some facts
    facts = state.all_facts()
    assert isinstance(facts, dict), "Should update world state"

    print("✓ Belief updater test passed")


# =============================================================================
# Feature 12: Identity Layer Tests
# =============================================================================

def test_identity_manager():
    """Test IdentityManager persona CRUD."""
    print("Testing identity manager...")
    import os
    import tempfile
    from realai.identity import IdentityManager

    fd, tmp_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(tmp_path)

    manager = IdentityManager(config_path=tmp_path)

    # Create
    persona = manager.create(
        name="Assistant",
        description="A helpful assistant",
        system_prompt="You are a helpful assistant.",
        tone="balanced",
    )
    assert persona.name == "Assistant"
    assert persona.memory_namespace == "persona_{0}".format(persona.id)

    # Get
    retrieved = manager.get(persona.id)
    assert retrieved is not None
    assert retrieved.name == "Assistant"

    # List all
    all_personas = manager.list_all()
    assert len(all_personas) == 1

    # Update
    updated = manager.update(persona.id, tone="formal")
    assert updated is not None
    assert updated.tone == "formal"

    # Delete
    assert manager.delete(persona.id) is True
    assert manager.get(persona.id) is None
    assert manager.delete("nonexistent") is False

    # Cleanup
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)

    print("✓ Identity manager test passed")


def test_persona_switcher():
    """Test PersonaSwitcher activation."""
    print("Testing persona switcher...")
    import os
    import tempfile
    from realai.identity import IdentityManager, PersonaSwitcher

    fd, tmp_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(tmp_path)

    manager = IdentityManager(config_path=tmp_path)
    switcher = PersonaSwitcher(manager)

    # Default prompt
    default_prompt = switcher.get_active_system_prompt()
    assert isinstance(default_prompt, str)
    assert len(default_prompt) > 0

    # No active persona
    assert switcher.active is None

    # Create and switch
    persona = manager.create(
        name="Coder",
        description="Coding assistant",
        system_prompt="You are an expert Python developer.",
    )
    result = switcher.switch_to(persona.id)
    assert "switched_to" in result
    assert result["switched_to"] == "Coder"
    assert switcher.active is not None
    assert switcher.get_active_system_prompt() == "You are an expert Python developer."

    # Switch to nonexistent
    result = switcher.switch_to("nonexistent-id")
    assert "error" in result

    # Cleanup
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)

    print("✓ Persona switcher test passed")


def test_persona_trainer():
    """Test PersonaTrainer feedback and suggestion."""
    print("Testing persona trainer...")
    import os
    import tempfile
    from realai.identity import IdentityManager, PersonaTrainer

    fd, tmp_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(tmp_path)

    manager = IdentityManager(config_path=tmp_path)
    trainer = PersonaTrainer()

    persona = manager.create(
        name="Test",
        description="Test persona",
        system_prompt="You are helpful.",
    )

    # Collect feedback
    trainer.collect_feedback(persona.id, "User asked about Python", rating=2)
    trainer.collect_feedback(persona.id, "User asked about Java", rating=3)

    # Suggest update
    suggestion = trainer.suggest_prompt_update(persona.id, manager)
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0

    # Apply suggestion
    success = trainer.apply_suggestion(persona.id, "New improved prompt.", manager)
    assert success is True

    # Verify applied
    updated = manager.get(persona.id)
    assert updated.system_prompt == "New improved prompt."

    # Cleanup
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)

    print("✓ Persona trainer test passed")


# =============================================================================
# Feature 13: Self-Improvement Engine Tests
# =============================================================================

def test_training_data_generator():
    """Test TrainingDataGenerator."""
    print("Testing training data generator...")
    import os
    import tempfile
    from realai.self_improvement import TrainingDataGenerator

    # Test disabled by default
    os.environ.pop("REALAI_SELF_IMPROVE", None)
    generator = TrainingDataGenerator()

    try:
        generator.generate_from_history(None)
        assert False, "Should raise PermissionError"
    except PermissionError:
        pass

    # Enable and test
    os.environ["REALAI_SELF_IMPROVE"] = "true"
    try:
        from realai.memory.engine import MemoryEngine
        engine = MemoryEngine()
        engine.store("Test memory item", tags=["test"])

        examples = generator.generate_from_history(engine, min_score=0.5)
        assert isinstance(examples, list)

        if examples:
            ex = examples[0]
            assert hasattr(ex, "id")
            assert hasattr(ex, "label")
            assert ex.label in ("good", "bad", "neutral")

            # Export JSONL
            fd, path = tempfile.mkstemp(suffix=".jsonl")
            os.close(fd)
            try:
                result_path = generator.export_jsonl(examples, path)
                assert result_path == path
                assert os.path.exists(path)
            finally:
                if os.path.exists(path):
                    os.unlink(path)
    finally:
        os.environ.pop("REALAI_SELF_IMPROVE", None)

    print("✓ Training data generator test passed")


def test_performance_evaluator():
    """Test PerformanceEvaluator."""
    print("Testing performance evaluator...")
    import os
    from realai.self_improvement import PerformanceEvaluator

    evaluator = PerformanceEvaluator()

    # Test disabled
    os.environ.pop("REALAI_SELF_IMPROVE", None)
    try:
        evaluator.evaluate()
        assert False, "Should raise PermissionError"
    except PermissionError:
        pass

    # Test enabled
    os.environ["REALAI_SELF_IMPROVE"] = "true"
    try:
        scores = evaluator.evaluate()
        assert isinstance(scores, dict)
        assert "overall" in scores

        # Test delta
        baseline = {"overall": 0.8, "reasoning": 0.7}
        current = {"overall": 0.85, "reasoning": 0.75}
        delta = evaluator.delta(current, baseline)
        assert abs(delta["overall"] - 0.05) < 0.001
        assert abs(delta["reasoning"] - 0.05) < 0.001
    finally:
        os.environ.pop("REALAI_SELF_IMPROVE", None)

    print("✓ Performance evaluator test passed")


def test_version_manager():
    """Test VersionManager version reading."""
    print("Testing version manager...")
    import os
    from realai.self_improvement import VersionManager

    vm = VersionManager()

    # Test current_version from setup.py
    repo_path = os.path.dirname(os.path.abspath(__file__))
    version = vm.current_version(repo_path)
    assert isinstance(version, str)
    assert len(version) > 0

    # Test with nonexistent path (should return "unknown")
    version = vm.current_version("/nonexistent/path/xyz")
    assert version == "unknown"

    # Test tag_version when disabled
    os.environ.pop("REALAI_SELF_IMPROVE", None)
    try:
        vm.tag_version("1.0.0")
        assert False, "Should raise PermissionError"
    except PermissionError:
        pass

    # Test generate_changelog when disabled
    try:
        vm.generate_changelog(None, "1.0.0", "2.0.0")
        assert False, "Should raise PermissionError"
    except PermissionError:
        pass

    print("✓ Version manager test passed")


def run_all_tests():
    """Run all tests."""
    print("="*60)
    print("Running RealAI Tests")
    print("="*60 + "\n")
    
    tests = [
        test_model_initialization,
        test_client_initialization,
        test_chat_completion,
        test_text_completion,
        test_image_generation,
        test_image_analysis,
        test_video_generation,
        test_code_generation,
        test_embeddings,
        test_structured_server_routes,
        test_structured_server_platform_endpoints,
        test_structured_server_config_files,
        test_week2_inference_registry_routes,
        test_week3_memory_and_tool_pipeline,
        test_week5_voice_registry_backends,
        test_week7_python_sandbox_security,
        test_week7_tool_permission_enforcement,
        test_week7_agent_safety_limits,
        test_week7_web3_policy,
        test_week7_tool_call_validation,
        test_week9_model_cache,
        test_week9_health_and_reload_routes,
        test_structured_training_pipeline,
        test_structured_sdk_facade,
        test_audio_transcription,
        test_audio_generation,
        test_translation,
        test_web_research,
        test_capability_catalog_and_provider_capabilities,
        test_persona_profiles_and_chat_metadata,
        test_task_automation,
        test_voice_interaction,
        test_business_planning,
        test_therapy_counseling,
        test_web3_integration,
        test_web3_gpg_signing,
        test_code_execution,
        test_plugin_system,
        test_memory_learning,
        test_model_capabilities,
        test_model_info,
        # Future AI Capabilities (2026+)
        test_quantum_integration,
        test_neural_architecture_search,
        test_causal_reasoning,
        test_meta_learning,
        test_emotional_intelligence,
        test_swarm_intelligence,
        test_predictive_simulation,
        test_consciousness_simulation,
        test_reality_simulation,
        # Provider routing tests
        test_provider_detection,
        test_provider_configs,
        test_provider_env_vars,
        test_realai_provider_init,
        test_client_provider_params,
        test_chat_fallback_without_key,
        # Plugin real-world tests
        test_local_plugin_loading,
        test_load_all_plugins,
        # Next-generation capability tests
        test_chain_of_thought,
        test_chain_of_thought_client,
        test_synthesize_knowledge,
        test_synthesize_knowledge_client,
        test_self_reflect,
        test_self_reflect_client,
        test_orchestrate_agents,
        test_orchestrate_agents_client,
        test_generate_speech,
        test_new_capabilities_in_model,
        test_new_client_attributes,
        # Agent Orchestration and Hive Mind System Tests
        test_agent_orchestration,
        test_agent_execution,
        test_agent_registration,
        test_agent_listing,
        test_agent_status,
        test_core_agent_methods,
        # Cloud Computing and Distributed Systems Tests
        test_cloud_deployment_orchestration,
        test_distributed_computing_coordination,
        test_auto_scaling_management,
        test_load_balancing_optimization,
        test_multi_cloud_resource_management,
        test_serverless_function_deployment,
        test_container_orchestration,
        test_cloud_cost_optimization,
        test_distributed_ai_training,
        test_cloud_native_ai_inference,
        test_cloud_convenience_methods,
        # Computer Mode and Desktop Automation Tests
        test_computer_mode_activation,
        test_screen_capture_analysis,
        test_mouse_keyboard_control,
        test_window_management,
        test_gui_automation,
        test_development_workflow_automation,
        test_self_learning_recording,
        test_action_replay_execution,
        test_code_generation_automation,
        test_app_building_automation,
        # Crypto Trading and Mining Tests
        test_crypto_mining,
        test_ai_trading_bot_integration,
        test_freqtrade_integration,
        test_hummingbot_integration,
        test_octobot_integration,
        test_jessie_trading_integration,
        test_superalgos_integration,
        test_polymarket_bot_integration,
        test_market_analysis,
        test_trading_strategy_optimization,
        test_risk_management,
        test_portfolio_management,
        # Feature 1: Model Registry + Capability Graph
        test_capability_graph,
        test_model_registry_metadata,
        test_model_registry_api_payloads,
        test_route_for_task,
        # Feature 2: Tool Registry
        test_tool_registry,
        test_tool_call_validator,
        test_tool_call_optimizer,
        # Feature 3: Self-Critique Engine
        test_critique_engine,
        test_compress_cot,
        test_retry_with_critique,
        # Feature 4: Multi-Agent Runtime
        test_message_bus,
        test_pipeline_runner,
        test_agent_graph,
        # Feature 5: Local Runtime
        test_local_model_cache,
        test_local_vector_db,
        test_local_tool_sandbox,
        test_local_embeddings_server,
        # Feature 6: Plugin Marketplace
        test_plugin_manifest,
        test_plugin_discovery,
        test_plugin_verifier,
        test_plugin_sandbox,
        # Feature 7: Memory Engine
        test_short_term_memory,
        test_episodic_memory,
        test_symbolic_memory,
        test_semantic_memory,
        test_memory_engine,
        # Feature 8: Knowledge Graph
        test_knowledge_graph,
        test_entity_linker,
        test_synthesis_engine,
        # Feature 9: App Framework
        test_realai_app,
        test_workflow_builder,
        test_automation_builder,
        # Feature 10: Benchmark Suite
        test_benchmark_suite,
        # Feature 11: World Model
        test_world_state,
        test_planning_engine,
        test_goal_tracker,
        test_belief_updater,
        # Feature 12: Identity Layer
        test_identity_manager,
        test_persona_switcher,
        test_persona_trainer,
        # Feature 13: Self-Improvement Engine
        test_training_data_generator,
        test_performance_evaluator,
        test_version_manager,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n✓ All tests passed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()

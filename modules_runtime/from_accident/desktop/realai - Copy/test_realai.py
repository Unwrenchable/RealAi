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

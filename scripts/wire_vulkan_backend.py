
from pathlib import Path
from realai.plugins.local_models import LocalModelManager, LocalModelType, LocalLLMEngine

mgr = LocalModelManager()
models_dir = Path(r'C:\RealAI-clean\models')
for name, filename in [
    ('qwen-coder-7b', 'qwen2.5-coder-7b-instruct-q5_k_m.gguf'),
    ('realai-1.0', 'realai-1.0-instruct-Q4_K_M.gguf'),
]:
    path = models_dir / filename
    if not path.exists():
        print('SKIP', name)
        continue
    mgr.register_model(name, LocalModelType.LLM, {
        'path': str(path),
        'backend': 'vulkan-http',
        'api_base': 'http://127.0.0.1:8080/v1',
        'context_length': 16384,
        'gpu_layers': 99,
    })
    print('registered', name)

eng = LocalLLMEngine(mgr)
ok = eng.load_model('qwen-coder-7b')
print('loaded:', ok, eng.is_loaded(), eng.get_current_model())
if ok:
    print(eng.generate('Say hello in one short sentence.', max_tokens=40))
else:
    print('Load failed — is Vulkan server running on :8080?')

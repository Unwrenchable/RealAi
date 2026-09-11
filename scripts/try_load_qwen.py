from realai.plugins.local_models import LocalModelManager, LocalLLMEngine

mgr = LocalModelManager()
engine = LocalLLMEngine(mgr)
print("Loading qwen-coder-7b ...")
ok = engine.load_model("qwen-coder-7b")
print("load returned:", ok, "is_loaded:", engine.is_loaded(), "model:", engine.get_current_model())
if ok:
    out = engine.generate("Say hello in one short sentence.", max_tokens=40)
    print("generate:", out)
else:
    print("Load failed — check path and llama-cpp backend")

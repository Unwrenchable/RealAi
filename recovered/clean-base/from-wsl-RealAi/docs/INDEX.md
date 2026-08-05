# 📚 RealAI Local Llama.cpp - Complete Documentation Index

Welcome to the comprehensive documentation for running RealAI with local llama.cpp models!

## 🎯 Quick Navigation

### For New Users
- **[QUICKSTART_LOCAL.md](../QUICKSTART_LOCAL.md)** - Get running in 5 minutes
- **[LOCAL_LLAMA_README.md](LOCAL_LLAMA_README.md)** - Overview and benefits

### For Existing RealAI Users
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Switch from cloud to local

### For Technical Details
- **[local-llama-setup.md](local-llama-setup.md)** - Complete setup guide
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Technical implementation details

### For Developers
- **[architecture.md](architecture.md)** - RealAI architecture overview
- Source code: `realai/server/llama_cli_backend.py`

## 📖 Document Overview

### QUICKSTART_LOCAL.md
**Quick reference card for rapid setup**

**Contains**:
- 3-command quick start
- Essential commands
- API usage examples
- Troubleshooting quick fixes
- Success checklist

**Best for**: Users who want to get started immediately with minimal reading

---

### LOCAL_LLAMA_README.md
**High-level overview and benefits**

**Contains**:
- What is local llama.cpp integration
- Benefits (privacy, cost, performance, offline)
- Quick start instructions
- Architecture diagrams
- API compatibility information
- Performance benchmarks

**Best for**: Decision-makers and users evaluating whether to use local inference

---

### local-llama-setup.md
**Comprehensive setup and configuration guide**

**Contains**:
- Detailed installation instructions
- Configuration examples
- Advanced features (GPU, multiple models, tuning)
- Complete troubleshooting guide
- API endpoints documentation
- Performance optimization tips

**Best for**: Users doing initial setup or troubleshooting issues

---

### MIGRATION_GUIDE.md
**Guide for migrating from cloud to local**

**Contains**:
- Step-by-step migration process
- Migration strategies (full, hybrid, gradual)
- Configuration updates
- Client code changes
- Cost comparison
- Rollback plan

**Best for**: Existing RealAI users switching from cloud APIs

---

### IMPLEMENTATION_SUMMARY.md
**Technical implementation details**

**Contains**:
- Implementation overview
- Architecture details
- File structure
- Backend selection logic
- Performance characteristics
- Test results

**Best for**: Developers and contributors understanding the implementation

---

## 🛠️ Practical Tools

### Setup Checker
**File**: `scripts/setup_local_llama.py`

**Purpose**: Automated verification of your installation

**Run**:
```powershell
python scripts/setup_local_llama.py
```

**Checks**:
- ✅ llama-cli availability
- ✅ GGUF models presence
- ✅ Registry configuration
- ✅ Python dependencies
- ✅ Server startup capability

---

### Example Scripts
**File**: `examples/local_llama_example.py`

**Purpose**: Demonstrate common usage patterns

**Run**:
```powershell
python examples/local_llama_example.py
```

**Includes**:
- Simple chat completion
- Technical questions
- Multi-turn conversations
- Performance benchmarking
- Error handling

---

### Integration Tests
**File**: `tests/test_local_llama_integration.py`

**Purpose**: Validate implementation correctness

**Run**:
```powershell
python -m pytest tests/test_local_llama_integration.py -v
```

**Tests**:
- Backend initialization
- llama-cli detection
- Text generation
- Backend selection
- Model registry validation
- Documentation completeness

---

## 📂 Configuration Files

### Model Registry
**File**: `realai/models/registry.json`

**Purpose**: Define available models and their configurations

**Example**:
```json
{
  "llama-local": {
	"type": "chat",
	"backend": "llama-cli",
	"path": "C:/Users/tsmit/models/llama-3.2-3b-instruct.Q4_K_M.gguf",
	"context_length": 8192
  }
}
```

**Template**: `realai/models/registry.json.example`

---

### Server Configuration
**File**: `realai.toml`

**Purpose**: Configure server behavior and backend settings

**Example**:
```toml
[server]
default_chat_model = "llama-local"

[backends.llama-cli]
llama_cli_path = "C:/llama.cpp/llama-cli.exe"
```

**Template**: `realai.toml.example`

---

## 🚀 Usage Workflows

### Workflow 1: First-Time Setup

1. Read **QUICKSTART_LOCAL.md**
2. Download llama-cli and GGUF model
3. Configure `realai/models/registry.json`
4. Run `python scripts/setup_local_llama.py`
5. Start server: `python -m realai.server.app`
6. Test with `python examples/local_llama_example.py`

---

### Workflow 2: Troubleshooting

1. Run `python scripts/setup_local_llama.py`
2. Check **local-llama-setup.md** → Troubleshooting section
3. Review logs in console output
4. Verify paths in `realai/models/registry.json`
5. Test llama-cli manually: `llama-cli --version`

---

### Workflow 3: Migration from Cloud

1. Read **MIGRATION_GUIDE.md**
2. Install llama.cpp (keep existing setup intact)
3. Add local models to registry (keep cloud models)
4. Start local server
5. Test local server with example scripts
6. Update client code to use local server
7. Monitor performance and quality
8. Gradually increase local usage

---

### Workflow 4: Performance Optimization

1. Read **local-llama-setup.md** → Advanced Features
2. Enable GPU acceleration (rebuild with CUDA)
3. Try different quantization levels (Q4_K_M vs Q5_K_M)
4. Tune sampling parameters (temperature, top_p)
5. Run benchmarks: `python examples/local_llama_example.py`
6. Adjust based on speed vs quality tradeoffs

---

## 📋 Cheat Sheets

### Essential Commands

```powershell
# Check setup
python scripts/setup_local_llama.py

# Start server (basic)
python -m realai.server.app

# Start server (with auto-reload)
uvicorn realai.server.app:app --reload

# Run examples
python examples/local_llama_example.py

# Run tests
python -m pytest tests/test_local_llama_integration.py -v

# Test endpoint
curl http://127.0.0.1:8000/health

# Test chat
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-local","messages":[{"role":"user","content":"Hello"}]}'
```

---

### File Locations

```
realai/
├── QUICKSTART_LOCAL.md           # Quick reference
├── realai.toml.example            # Config template
│
├── realai/
│   ├── models/
│   │   ├── registry.json          # Model configuration
│   │   └── registry.json.example  # Registry template
│   └── server/
│       ├── llama_cli_backend.py   # Backend implementation
│       └── backends.py            # Backend resolver
│
├── docs/
│   ├── LOCAL_LLAMA_README.md      # Overview
│   ├── local-llama-setup.md       # Complete guide
│   ├── MIGRATION_GUIDE.md         # Migration steps
│   ├── IMPLEMENTATION_SUMMARY.md  # Technical details
│   └── INDEX.md                   # This file
│
├── scripts/
│   └── setup_local_llama.py       # Setup checker
│
├── examples/
│   └── local_llama_example.py     # Usage examples
│
└── tests/
	└── test_local_llama_integration.py  # Integration tests
```

---

### Quick Troubleshooting

| Problem | Solution | Reference |
|---------|----------|-----------|
| llama-cli not found | Add to PATH or configure in realai.toml | [Setup Guide](local-llama-setup.md#troubleshooting) |
| Model not found | Check path in registry.json | [Setup Guide](local-llama-setup.md#model-not-loading) |
| Slow inference | Enable GPU or use smaller model | [Setup Guide](local-llama-setup.md#slow-inference) |
| Out of memory | Use aggressive quantization (Q3_K_M) | [Setup Guide](local-llama-setup.md#out-of-memory) |
| Server won't start | Check dependencies: `pip install fastapi uvicorn` | [Quick Start](../QUICKSTART_LOCAL.md) |

---

## 🎓 Learning Path

### Beginner
1. **Read**: [QUICKSTART_LOCAL.md](../QUICKSTART_LOCAL.md)
2. **Do**: Follow 3-command quick start
3. **Verify**: Run `python scripts/setup_local_llama.py`
4. **Test**: Run `python examples/local_llama_example.py`

### Intermediate
1. **Read**: [local-llama-setup.md](local-llama-setup.md)
2. **Do**: Configure multiple models
3. **Optimize**: Tune sampling parameters
4. **Benchmark**: Compare different models and quantizations

### Advanced
1. **Read**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
2. **Extend**: Add custom backends or endpoints
3. **Contribute**: Submit improvements or bug fixes
4. **Deploy**: Set up production server with monitoring

---

## 🔗 External Resources

### llama.cpp
- **GitHub**: https://github.com/ggerganov/llama.cpp
- **Releases**: https://github.com/ggerganov/llama.cpp/releases
- **Documentation**: https://github.com/ggerganov/llama.cpp/blob/master/README.md

### GGUF Models
- **Hugging Face Search**: https://huggingface.co/models?search=gguf
- **Llama Models**: https://huggingface.co/bartowski
- **TheBloke's Models**: https://huggingface.co/TheBloke

### RealAI
- **GitHub**: https://github.com/Unwrenchable/realai
- **Architecture**: [docs/architecture.md](architecture.md)

---

## 📞 Getting Help

### Self-Service
1. Run setup checker: `python scripts/setup_local_llama.py`
2. Check relevant documentation section above
3. Review example scripts: `examples/local_llama_example.py`
4. Check integration tests: `tests/test_local_llama_integration.py`

### Documentation Search
- **Setup issues**: [local-llama-setup.md](local-llama-setup.md) → Troubleshooting
- **Migration questions**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **API usage**: [LOCAL_LLAMA_README.md](LOCAL_LLAMA_README.md) → API Compatibility
- **Performance**: [local-llama-setup.md](local-llama-setup.md) → Performance Tuning

---

## ✅ Success Criteria

By the end of your setup, you should have:

- [ ] llama-cli.exe installed and accessible
- [ ] At least one GGUF model downloaded
- [ ] `realai/models/registry.json` configured correctly
- [ ] Local server starting without errors
- [ ] Health endpoint returning `"status": "ok"`
- [ ] Chat completions working correctly
- [ ] Setup checker passing all tests
- [ ] Zero dependency on cloud API keys

**All green?** 🎉 You're ready to use RealAI locally!

---

## 🆕 Recent Updates

### Version 1.0 (2025)
- ✅ Initial llama-cli backend implementation
- ✅ Backend resolver integration
- ✅ Model registry updates
- ✅ Comprehensive documentation
- ✅ Setup tools and examples
- ✅ Integration tests

### Coming Soon
- 🔜 Streaming response support
- 🔜 Embeddings endpoint
- 🔜 Reranking models
- 🔜 Multi-model routing
- 🔜 Web UI for model management

---

## 📝 Documentation Maintenance

### For Contributors

When updating documentation:
1. Update relevant section in appropriate file
2. Update this INDEX.md if structure changes
3. Run tests: `python -m pytest tests/test_local_llama_integration.py`
4. Verify examples still work: `python examples/local_llama_example.py`
5. Update version history in this file

### Document Owners
- **QUICKSTART_LOCAL.md**: Quick reference team
- **LOCAL_LLAMA_README.md**: Documentation team
- **local-llama-setup.md**: Documentation team
- **MIGRATION_GUIDE.md**: Migration specialists
- **IMPLEMENTATION_SUMMARY.md**: Development team

---

**Last Updated**: 2025  
**Documentation Version**: 1.0  
**Implementation Status**: ✅ Complete and Production-Ready

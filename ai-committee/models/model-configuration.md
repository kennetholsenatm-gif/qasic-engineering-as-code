# Ollama Model Configuration for QASIC Committee

## Model Selection Strategy

Each agent is assigned an Ollama model based on:
1. **Speed**: How quickly the agent needs to respond
2. **Reasoning**: Complexity of reasoning required for the domain
3. **Specialization**: Fit to the task domain
4. **Resource Budget**: Memory and compute constraints

---

## Committee Model Assignments

| Agent | Model | Size | Speed | Reasoning | Notes |
|-------|-------|------|-------|-----------|-------|
| **Quantum Protocol Specialist** | `neural-chat` | ~13B | Fast | Medium | Strong at explanations, protocol design |
| **Engineering Pipeline Expert** | `mistral` | ~7B | Fast | Strong | Excellent reasoning, good for complex logic |
| **Backend/API Developer** | `openchat` | ~8B | Fast | Medium | Good at code, API design |
| **Frontend Developer** | `openchat` | ~8B | Fast | Medium | Solid React/JS knowledge |
| **Infrastructure/DevOps** | `mistral` | ~7B | Fast | Strong | Infrastructure reasoning, Terraform/Helm |
| **Documentation Manager** | `neural-chat` | ~13B | Fast | Medium | Good at comprehensive writing |
| **QA/Testing Specialist** | `openchat` | ~8B | Fast | Medium | Quality assurance, test design |
| **Project Manager/Coordinator** | `neural-chat` | ~13B | Fast | Medium | Planning, coordination, summarization |

---

## Pull Models From Ollama

### Required (for full committee)
```powershell
ollama pull neural-chat      # 13B, fast, good writer
ollama pull mistral          # 7B, strong reasoning
ollama pull openchat         # 8B, code/API focused
```

**Total**: ~28-30GB disk, ~16GB RAM for inference

### Optional (larger/better models)
```powershell
ollama pull llama2           # 13B, general purpose
ollama pull dolphin-mixtral  # 120B, very strong reasoning (slow)
ollama pull wizard-math      # Specialized for math
```

---

## Model Profiles

### neural-chat (Recommended: 13B, 8GB RAM)
**Pros:**
- Balanced speed and quality
- Excellent at explanations and writing
- Good for documentation and protocol descriptions
- Friendly, conversational tone

**Cons:**
- Not as strong at complex code
- Slower than smaller models

**Best for:** Quantum Protocol Specialist, Documentation Manager, PM Coordinator

**Pull:**
```bash
ollama pull neural-chat
```

---

### mistral (Recommended: 7B, 4-8GB RAM)
**Pros:**
- Excellent reasoning for complex problems
- Strong at infrastructure/DevOps concepts
- Fast for its reasoning capability
- Good instruction following

**Cons:**
- Can be verbose
- Not specialized for any single domain

**Best for:** Engineering Pipeline Expert, Infrastructure/DevOps

**Pull:**
```bash
ollama pull mistral
```

---

### openchat (Recommended: 8B, 6-8GB RAM)
**Pros:**
- Good at code and technical content
- Follows instructions well
- Decent reasoning
- Relatively fast

**Cons:**
- Occasional hallucinations on unfamiliar topics
- Not as good at writing prose

**Best for:** Backend/API, Frontend, QA/Testing

**Pull:**
```bash
ollama pull openchat
```

---

## Alternative Model Suggestions

If your resources differ, consider:

### For Constrained Resources (4GB RAM)
```powershell
ollama pull orca-mini       # 3B, minimal
ollama pull phi             # 2.7B, efficient
```

### For Better Reasoning (16GB+ RAM)
```powershell
ollama pull llama2-uncensored   # 13B, no restrictions
ollama pull dolphin-mixtral      # 120B, excellent (very slow)
```

### Specialized Models
```powershell
ollama pull wizard-math          # Math/reasoning optimization
ollama pull deepseek-coder       # Code specialization
ollama pull neural-chat:7b       # Smaller variant if needed
```

---

## Configuration Files

### Environment Setup
Create `.env.ollama` in the `ai-committee/` directory:

```bash
# .env.ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_NUM_GPU=1   # GPU acceleration (if available)
OLLAMA_NUM_PARALLEL=2  # Run 2 models in parallel

# Optional: Model-specific parameters
NEURAL_CHAT_CONTEXT_LENGTH=4096
MISTRAL_CONTEXT_LENGTH=8192
OPENCHAT_CONTEXT_LENGTH=4096

# Committee settings
COMMITTEE_LOG_DIR=./logs
COMMITTEE_RESPONSE_TIMEOUT=120  # seconds
```

### Python Configuration
In `orchestrator.py`, load from `.env`:

```python
from dotenv import load_dotenv
load_dotenv('.env.ollama')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
```

---

## Performance Tuning

### Context Length Settings
Adjust based on your use case:

```python
# In orchestrator.py, per-agent context
requests.post(
    f"{self.base_url}/api/generate",
    json={
        "model": "mistral",
        "prompt": task,
        "num_ctx": 2048,  # Context window
        "num_predict": 512,  # Max response length
        "temperature": 0.7,  # Creativity (0.0-1.0)
    }
)
```

### Recommended Settings by Agent

**Quantum Protocol Specialist (neural-chat)**
```
num_ctx: 4096
num_predict: 512
temperature: 0.8  # Higher creativity for ideation
```

**Engineering Pipeline Expert (mistral)**
```
num_ctx: 8192  # Need more context for complex designs
num_predict: 1024
temperature: 0.5  # Lower for precision
```

**Backend/API Developer (openchat)**
```
num_ctx: 4096
num_predict: 1024  # Code can be long
temperature: 0.3  # Very precise for code
```

---

## Running Ollama for Committee

### Start Ollama Service
```powershell
# On Windows (if running as service)
Restart-Service ollama

# Or run interactively
ollama serve
```

### Verify Models Loaded
```bash
curl http://localhost:11434/api/tags
```

Should return JSON with all pulled models.

### Test Single Agent
```python
from orchestrator import CommitteeOrchestrator, AgentRole

orch = CommitteeOrchestrator()
result = orch.query_agent(
    AgentRole.QUANTUM_PROTOCOL,
    "Explain Bell pair preparation for the QASIC 3-qubit chain"
)
print(result)
```

---

## Resource Monitoring

### Check Ollama Memory Usage
```powershell
# Check running processes
Get-Process ollama | Select-Object ProcessName, WorkingSet

# Monitor GPU usage (if using CUDA/Metal)
nvidia-smi  # NVIDIA GPUs
```

### Ollama Logs
```bash
# View Ollama server logs
# On Windows: C:\Users\[user]\AppData\Local\Ollama\logs
# On Mac: ~/.ollama/logs
# On Linux: ~/.local/share/ollama/logs
```

### Performance Optimization
If models run too slow:
1. Reduce `num_predict` (max response length)
2. Reduce `num_ctx` (context window)
3. Lower `num_parallel` (run fewer models at once)
4. Switch to smaller model (e.g., `orca-mini`)

---

## Troubleshooting

### Model Download Fails
```bash
# Check Ollama connectivity
curl https://ollama.com/api/status

# Retry with larger timeout
ollama pull mistral --timeout 3600
```

### Out of Memory Errors
1. Close other applications
2. Use smaller models (`orca-mini`, `phi`)
3. Reduce `num_parallel` in `.env.ollama`
4. Reduce `num_ctx` per query

### Slow Responses
1. Check GPU acceleration: `ollama -v` (should show GPU info)
2. Reduce model complexity
3. Check system resources (Task Manager → Performance)
4. Ensure models are not swapping to disk

### Model Not Found
```bash
# List available models
ollama list

# Pull if missing
ollama pull neural-chat
```

---

## Next Steps

1. **Install Ollama** (if not done): https://ollama.com/download
2. **Pull required models**: `ollama pull neural-chat && ollama pull mistral && ollama pull openchat`
3. **Start Ollama server**: `ollama serve`
4. **Test connection**: `python orchestrator.py` (should print roster)
5. **Run committee query**: See examples in `orchestrator.py`
6. **Integrate with VS Code**: See `vs-code-integration.md`

---

## References
- Ollama: https://ollama.com
- Model details: https://ollama.com/library
- GPU acceleration: https://github.com/ollama/ollama#gpu-acceleration

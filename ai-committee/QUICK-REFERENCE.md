# QASIC AI Committee - Quick Reference

**Your 8-member AI committee for executing the QASIC Engineering-as-Code vision.**

---

## 🏛️ Committee Roster

| Agent | Model | Key Domains | Shortcut |
|-------|-------|-------------|----------|
| **Quantum Protocol Specialist** | neural-chat | Entanglement, QKD, 3-qubit ASIC circuits | `Ctrl+Shift+Alt+P` |
| **Engineering Pipeline Expert** | mistral | Routing, inverse design, HEaC, GDS, DRC | `Ctrl+Shift+Alt+E` |
| **Backend/API Developer** | openchat | FastAPI, Celery, dispatcher, async orchestration | - |
| **Frontend Developer** | openchat | React, Vite, WebSocket streaming, UI/UX | - |
| **Infrastructure/DevOps Expert** | mistral | Docker, Kubernetes, Helm, OpenTofu, CI/CD | - |
| **Documentation Manager** | neural-chat | Tech writing, whitepapers, API docs, roadmaps | - |
| **QA/Testing Specialist** | openchat | Pytest, CI baselines, regression testing | - |
| **Project Manager/Coordinator** | neural-chat | Planning, risk management, coordination | `Ctrl+Shift+Q` (routes others) |

---

## ⚡ Quick Commands

### Start Ollama
```powershell
ollama serve
```

### Pull Models
```bash
ollama pull neural-chat mistral openchat
```

### Query Committee (Python)
```python
from orchestrator import CommitteeOrchestrator, AgentRole
orch = CommitteeOrchestrator()

# Ask one agent
result = orch.query_agent(AgentRole.QUANTUM_PROTOCOL, "Your question")

# Route to appropriate agents
results = orch.route_task("Your complex question")

# Get all perspectives
results = orch.brainstorm_committee("Strategic question")
```

### Query Committee (VS Code)
- **Full committee**: `Ctrl+Shift+Q`
- **Quantum specialist**: `Ctrl+Shift+Alt+P`
- **Engineering expert**: `Ctrl+Shift+Alt+E`

### Interactive Notebook
```bash
jupyter notebook ai-committee/notebooks/committee-meeting.ipynb
```

---

## 📁 File Structure

```
ai-committee/
├── README.md                           ← Start here (full setup guide)
├── orchestrator.py                     ← Main committee coordinator
├── requirements.txt                    ← Python dependencies
├── agents/
│   └── agent-specs.md                 ← Detailed agent roles & expertise
├── models/
│   └── model-configuration.md         ← Ollama model setup & tuning
├── VS-CODE-INTEGRATION.md             ← IDE integration methods
└── notebooks/
    └── committee-meeting.ipynb        ← Interactive AI committee session
```

---

## 🚀 Getting Started

### 1. Setup (10 minutes)
```powershell
# Install Ollama
irm https://ollama.com/install.ps1 | iex

# Pull models  
ollama pull neural-chat mistral openchat

# Verify
python ai-committee/orchestrator.py
```

### 2. First Query (2 minutes)
```python
from orchestrator import CommitteeOrchestrator, AgentRole
orch = CommitteeOrchestrator()
result = orch.query_agent(
    AgentRole.QUANTUM_PROTOCOL,
    "Explain the 3-qubit ASIC topology"
)
print(result)
```

### 3. Integrate with VS Code (5 minutes)
Follow **VS-CODE-INTEGRATION.md** → Method 1 (quickest)

---

## 🎯 Common Use Cases

### Quantum Circuit Design
```python
orch.query_agent(AgentRole.QUANTUM_PROTOCOL, 
    "Design Bell pair circuit for 0-1-2 chain")
```

### Engineering Pipeline Review
```python
orch.query_agent(AgentRole.ENGINEERING_PIPELINE,
    "Review the inverse design convergence")
```

### Sprint Planning
```python
results = orch.route_task(
    "Plan next sprint: priorities, risks, timeline")
```

### Architecture Decision
```python
results = orch.brainstorm_committee(
    "Should we extend Alpha scope? Pros/cons from all perspectives")
```

### Troubleshooting
```python
orch.query_agent(AgentRole.QA_TESTING,
    "Debug failing DRC checks in tape-out")
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| `Connection refused` | Run `ollama serve` first |
| `Model not found` | Run `ollama pull neural-chat` |
| `Out of memory` | Use smaller models or reduce `num_predict` |
| `Slow responses` | Check GPU acceleration, reduce context window |

---

## 📚 Key Resources

| Topic | File |
|-------|------|
| Full setup guide | `README.md` |
| Agent specifications | `agents/agent-specs.md` |
| Model configuration | `models/model-configuration.md` |
| VS Code integration | `VS-CODE-INTEGRATION.md` |
| AI committee sessions | `notebooks/committee-meeting.ipynb` |

---

## 🌟 Pro Tips

1. **Save decisions**: Use `json.dump()` in orchestrator to log committee decisions
2. **Context-aware queries**: Pass `context` dict to inform agent decisions
3. **Batch processing**: Process multiple tasks to build knowledge
4. **Custom prompts**: Modify `system_prompt` in `orchestrator.py` for your style
5. **Extend committee**: Add custom agents by extending `AgentRole` enum

---

## 📞 Committee Communication

### Direct Query
Ask a specific agent: `orch.query_agent(role, task)`

### Routed Query
Let PM decide who to ask: `orch.route_task(task)`

### Brainstorm
Get all perspectives: `orch.brainstorm_committee(topic)`

### Milestone Review
PM summarizes progress: `orch.summarize_progress(milestone)`

---

## 🎓 Educational Path

1. **Beginner**: Run `orchestrator.py`,  read roster
2. **Intermediate**: Query individual agents with Python
3. **Advanced**: Route complex tasks, customize prompts
4. **Expert**: Build VS Code extension, integrate CI/CD

---

## 📋 Integration Checklist

- [ ] Ollama installed and running
- [ ] Models pulled (neural-chat, mistral, openchat)
- [ ] Verified connection: `python orchestrator.py`
- [ ] Ran first query with Python
- [ ] Added VS Code tasks/keybindings
- [ ] Created Jupyter notebook
- [ ] Documented custom agents/prompts
- [ ] Backed up committee decisions to logs/

---

## 🔗 External Links

- **Ollama**: https://ollama.com
- **Model Library**: https://ollama.com/library
- **QASIC GitHub**: https://github.com/kennetholsenatm-gif/qasic-engineering-as-code
- **Your Local Repo**: `C:\Users\kenne\OneDrive\Documents\GitHub\qasic-engineering-as-code`

---

**Version:** 1.0  
**Status:** Production-ready  
**Last Updated:** March 2026  
**Committee Members:** 8 specialized AI agents  
**Default Model Size:** ~28-30GB total  
**Recommended RAM:** 16GB+  
**GPU:** Optional (accelerates responses 3-5x)

---

**Ready to execute your QASIC vision with AI-assisted coordination! 🚀**

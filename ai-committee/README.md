# QASIC AI Committee Setup Guide

**Complete guide to setting up and running your 8-member AI assistant committee for executing the QASIC Engineering-as-Code vision.**

---

## Quick Start (5 minutes)

### 1. Install Ollama
```powershell
# Windows: Download from https://ollama.com/download
irm https://ollama.com/install.ps1 | iex
```

### 2. Pull Required Models
```bash
ollama pull neural-chat
ollama pull mistral
ollama pull openchat
```

### 3. Start Committee
```powershell
cd C:\Users\kenne\OneDrive\Documents\GitHub\qasic-engineering-as-code\ai-committee
python orchestrator.py
```

You should see the committee roster printed.

---

## Full Setup (30 minutes)

### Prerequisites
- **Windows 10/11** with admin access
- **Python 3.9+** (verify: `python --version`)
- **Ollama installed** (https://ollama.com/download)
- Access to your QASIC repo at `C:\Users\kenne\OneDrive\Documents\GitHub\qasic-engineering-as-code`

### Step 1: Verify Python Environment

```powershell
# Check Python version
python --version

# Create virtual environment (optional but recommended)
python -m venv C:\Users\kenne\venv-qasic-committee
C:\Users\kenne\venv-qasic-committee\Scripts\Activate.ps1

# Install dependencies
pip install requests python-dotenv
```

### Step 2: Install/Verify Ollama

```powershell
# Verify Ollama installed
ollama --version

# Start Ollama service (run in background)
ollama serve
# Wait for: "Listening on 127.0.0.1:11434"
```

**In a new PowerShell window**, continue:

### Step 3: Pull Models

```bash
# This will download ~30GB total (can take 10-30 minutes)
ollama pull neural-chat      # DocumentationManager, QuantumSpecialist, PM
ollama pull mistral          # EngineeringPipeline, Infrastructure
ollama pull openchat         # Backend, Frontend, QA/Testing

# Verify models downloaded
ollama list
```

Expected output:
```
NAME               ID              SIZE      MODIFIED
neural-chat:latest ...             13B       2 minutes ago
mistral:latest     ...             7B        1 minute ago
openchat:latest    ...             8B        2 minutes ago
```

### Step 4: Configure Environment

Create `.env.ollama` in `ai-committee/`:

```bash
# .env.ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_NUM_GPU=1
OLLAMA_NUM_PARALLEL=2

# Optional: Adjust for your hardware
COMMITTEE_RESPONSE_TIMEOUT=120
COMMITTEE_LOG_DIR=./logs
```

### Step 5: Test Committee

```powershell
cd C:\Users\kenne\OneDrive\Documents\GitHub\qasic-engineering-as-code\ai-committee

# Run orchestrator to verify setup
python orchestrator.py
```

Should display:
```
✓ Connected to Ollama at http://localhost:11434
🏛️ QASIC AI Committee Roster:

  • Quantum Protocol Specialist (neural-chat)
    Expertise: Quantum protocols, 3-qubit ASIC
    
  • Engineering Pipeline Expert (mistral)
    Expertise: Metasurface routing, inverse design
    
  ... (6 more agents)
```

---

## Using the Committee

### Example 1: Query a Specific Agent

```python
from orchestrator import CommitteeOrchestrator, AgentRole

orch = CommitteeOrchestrator()

# Ask Quantum Specialist
result = orch.query_agent(
    AgentRole.QUANTUM_PROTOCOL,
    "Design a teleporation circuit for the 3-qubit ASIC"
)
print(result)
```

### Example 2: Committee Brainstorm

```python
# Get all agents' perspective on a question
results = orch.brainstorm_committee(
    "What are the top 3 risks for Alpha launch?"
)

for agent_role, response in results.items():
    print(f"\n{agent_role}:")
    print(response)
    print("-" * 80)
```

### Example 3: Route a Complex Task

```python
# PM decides which agents to query
results = orch.route_task(
    "We need to add thermal simulation to the metasurface pipeline. "
    "What are the implementation steps and timeline?"
)

for agent_role, response in results.items():
    print(f"\n{agent_role}:\n{response}\n")
```

### Example 4: Create Interactive Loop

```python
from orchestrator import CommitteeOrchestrator
import json

orch = CommitteeOrchestrator()

while True:
    print("\n" + "="*60)
    print("QASIC Committee Query")
    print("="*60)
    
    query = input("\nYour question (or 'quit' to exit): ").strip()
    if query.lower() == 'quit':
        break
    
    # Let PM route the task
    results = orch.route_task(query)
    
    for agent, response in results.items():
        print(f"\n📌 {agent}:")
        print(response)
        print("-" * 60)
```

---

## Advanced Usage

### 1. Customize Agent Prompts

Edit `orchestrator.py`, find the `_initialize_agents()` method, and modify `system_prompt` for any agent:

```python
agents[AgentRole.QUANTUM_PROTOCOL].system_prompt = """
Custom prompt for your needs...
Include specific constraints, style, etc.
"""
```

### 2. Add Custom Agents

```python
# In orchestrator.py, add to AgentRole enum and _initialize_agents():

class AgentRole(Enum):
    QUANTUM_PROTOCOL = "quantum-protocol-specialist"
    # ... existing roles ...
    CUSTOM_ROLE = "my-custom-role"

# Then in _initialize_agents():
agents[AgentRole.CUSTOM_ROLE] = AgentProfile(
    role=AgentRole.CUSTOM_ROLE,
    model="mistral",  # Choose a model
    description="My Custom Agent",
    expertise=["expertise1", "expertise2"],
    system_prompt="Your custom prompt here..."
)
```

### 3. Batch Task Processing

```python
# Process multiple tasks with same agent
tasks = [
    "Design Bell pair circuit",
    "Design teleportation circuit",
    "Design bit-flip code"
]

for task in tasks:
    result = orch.query_agent(AgentRole.QUANTUM_PROTOCOL, task)
    print(f"✓ {task}: {result[:100]}...")
```

### 4. Context-Aware Queries

```python
# Pass context to inform agent decisions
context = {
    "current_alpha_scope": "3-qubit linear chain only",
    "timeline": "Alpha MVP in 6 weeks",
    "constraints": ["No DRC/LVS for Alpha", "Simulation only"]
}

results = orch.route_task(
    "What's the minimum viable implementation for Alpha?",
    context=context
)
```

### 5. Logging and Persistence

```python
# Extend orchestrator to save responses
import json
from datetime import datetime

def save_committee_decision(topic, results, decision_id=None):
    if not decision_id:
        decision_id = datetime.now().isoformat()
    
    with open(f"logs/decision_{decision_id}.json", "w") as f:
        json.dump({
            "timestamp": decision_id,
            "topic": topic,
            "responses": results
        }, f, indent=2)
    
    return decision_id

# Usage
results = orch.brainstorm_committee("Should we extend Alpha scope?")
save_committee_decision("alpha-scope-expansion", results)
```

---

## Integration with VS Code

### Option 1: Command Palette Integration

Create a VS Code task to query committee:

1. Open `.vscode/tasks.json` in your repo
2. Add this task:

```json
{
  "label": "Query QASIC Committee",
  "type": "shell",
  "command": "python",
  "args": [
    "ai-committee/orchestrator.py"
  ],
  "problemMatcher": [],
  "presentation": {
    "echo": true,
    "reveal": "always"
  }
}
```

3. Run with `Ctrl+Shift+B` → Select "Query QASIC Committee"

### Option 2: Create a VS Code Extension

Structure for later extension development:

```
vs-code-committee/
├── src/
│   └── extension.ts           # Extension entry point
├── package.json               # Extension metadata
└── README.md

// Quick implementation:
export function activate(context: vscode.ExtensionContext) {
    let disposable = vscode.commands.registerCommand(
        'qasic-committee.query',
        () => {
            vscode.window.showInputBox().then((query) => {
                // Call orchestrator.py with query
                // Display results in webview
            });
        }
    );
    context.subscriptions.push(disposable);
}
```

### Option 3: Notebook Integration

Create `notebooks/committee-meeting.ipynb` for interactive committee sessions:

```python
# Cell 1: Import and initialize
from orchestrator import CommitteeOrchestrator, AgentRole
orch = CommitteeOrchestrator()

# Cell 2: Query specific agent
result = orch.query_agent(
    AgentRole.ENGINEERING_PIPELINE,
    "What's the status of HEaC integration?"
)
print(result)

# Cell 3: Brainstorm
results = orch.brainstorm_committee("How do we tackle performance optimization?")
# Results displayed in notebook
```

---

## Troubleshooting

### Ollama Connection Error
```
✗ Cannot connect to Ollama: Connection refused
```

**Solution:**
```powershell
# Verify Ollama is running
ollama serve

# Check if port 11434 is accessible
Test-NetConnection localhost -Port 11434
```

### Out of Memory
```
RuntimeError: CUDA out of memory
```

**Solutions:**
1. Close other applications
2. Use smaller models: `ollama pull orca-mini`
3. Reduce `num_parallel` in `.env.ollama`
4. Reduce context window in queries

### Model Not Found
```
Error: Model 'neural-chat' not found
```

**Solution:**
```bash
ollama pull neural-chat
ollama list  # Verify it's listed
```

### Slow Responses
1. Check task manager for system load
2. Verify GPU is being used: `ollama -v` should mention GPU
3. Reduce `num_predict` (maximum response length)
4. Use faster model: `mistral` or `openchat` instead of `neural-chat`

---

## File Structure

```
ai-committee/
├── orchestrator.py                 # Main committee coordinator
├── .env.ollama                     # Environment configuration
├── agents/
│   └── agent-specs.md             # Detailed agent specifications
├── models/
│   └── model-configuration.md     # Ollama model setup and tuning
├── prompts/
│   └── system-prompts.json        # Agent system prompts (future)
├── notebooks/
│   ├── committee-meeting.ipynb    # Interactive AI committee session
│   ├── quantum-specialist.ipynb   # Agent-specific notebooks
│   └── ...
├── logs/                          # Decision logs and committee minutes
└── README.md                      # This file
```

---

## Common Tasks

### Task 1: Quantum Circuit Design Review
```python
orch.query_agent(
    AgentRole.QUANTUM_PROTOCOL,
    "Review this circuit for correctness: [paste circuit]"
)
```

### Task 2: Engineering Pipeline Status
```python
orch.query_agent(
    AgentRole.ENGINEERING_PIPELINE,
    "What's the current status of tape-out readiness?"
)
```

### Task 3: Sprint Planning
```python
results = orch.route_task(
    "Plan the next 2-week sprint. What should be our top 3 priorities?"
)
```

### Task 4: Risk Assessment
```python
results = orch.brainstorm_committee(
    "Identify technical risks for next quarter"
)
```

### Task 5: Documentation Update
```python
orch.query_agent(
    AgentRole.DOCUMENTATION,
    "Update the Alpha customer docs with latest features"
)
```

---

## Next Steps

1. ✅ **Install Ollama** and pull models
2. ✅ **Test committee** with `python orchestrator.py`
3. ⏭️ **Run example queries** from "Using the Committee" section
4. ⏭️ **Create committee-meeting.ipynb** for interactive sessions
5. ⏭️ **Integrate with VS Code** (Option 1, 2, or 3 above)
6. ⏭️ **Automate workflows** (CI reviews, merge gates, etc.)
7. ⏭️ **Build VS Code extension** for seamless IDE integration

---

## Support & References

- **Ollama**: https://ollama.com
- **Model Library**: https://ollama.com/library
- **QASIC Repo**: https://github.com/kennetholsenatm-gif/qasic-engineering-as-code
- **ALPHA_SCOPE**: `docs/app/ALPHA_SCOPE.md`
- **Architecture**: `docs/app/ARCHITECTURE_OVERVIEW.md`

---

## Committee Charter (Visual)

```
          🏛️ QASIC AI COMMITTEE
          
    PM Coordinator (neural-chat)
           |
    ┌──────┼──────┬──────────┬─────────────┐
    |      |      |          |             |
    ▼      ▼      ▼          ▼             ▼
  Quantum Eng.   Backend   Frontend   Infrastructure
  Protocol Pipl.   API     React          DevOps
  (neural-chat) (mistral) (openchat)    (mistral)
  
    │      │      │          │             │
    └──────┼──────┼──────────┼─────────────┘
           │      │          │
           ▼      ▼          ▼
        Documentation    QA/Testing
        Manager         Specialist
        (neural-chat)   (openchat)
        
        ↓
    QASIC Vision Execution
```

---

**Last Updated:** March 2026  
**Status:** Ready for deployment  
**Next Review:** After first AI committee session (or as needed)

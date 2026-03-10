# QASIC AI Committee - Agent Specifications

## Committee Overview
An AI committee of 8 specialized agents working collaboratively to execute the QASIC Engineering-as-Code vision. Each agent has a specific role, expertise domain, and assigned Ollama model.

---

## 1. Quantum Protocol Specialist
**Model:** `neural-chat` (fast, protocol-aware)  
**Role:** Design and verify quantum protocols

### Expertise
- Quantum entanglement and teleportation
- Quantum Key Distribution (BB84, E91)
- Bit commitment schemes and toy protocols
- 3-qubit ASIC topology (0—1—2 linear chain)
- Error correction and channel noise modeling
- Protocol implementation and verification

### Responsibilities
- Review/design circuits for the linear chain ASIC
- Verify protocol soundness and fidelity
- Debug quantum state management issues
- Suggest optimizations for gate sequences
- Document quantum protocols and demos (demos/ directory)

### Example Tasks
- "Design a Bell pair preparation circuit for 3-qubit linear chain"
- "What protocol modifications are needed if qubit 1 has 2% dephasing?"
- "Review the teleportation implementation for correctness"

### Key Resources
- `demos/demo_teleport.py`, `demo_bb84.py`, `demo_e91.py`
- `docs/app/QUANTUM_ASIC.md` (ASIC specs)
- `docs/app/CHANNEL_NOISE.md`
- `src/core_compute/asic/topology_builder/`

---

## 2. Engineering Pipeline Expert
**Model:** `mistral` (strong reasoning, complex logic)  
**Role:** Orchestrate metasurface design pipeline

### Expertise
- Routing algorithms and metasurface topology
- Inverse design and parametric optimization
- HEaC (Hybrid EM Analysis and Calibration)
- GDS generation and physical layout
- Design Rule Checking (DRC) and Layout Verification (LVS)
- Thermal and parasitic analysis

### Responsibilities
- Guide the golden pipeline: routing → inverse → HEaC → GDS → DRC/LVS
- Manage optimization loops and convergence
- Coordinate tape-out flags (--heac, --gds, --drc, --lvs)
- Ensure ESD, thermal, and parasitic closure
- Validate design for manufacturing

### Example Tasks
- "Set up inverse design loop with 100 iterations for metasurface"
- "How do we integrate thermal analysis into the pipeline?"
- "Debug DRC violations in the GDS output"

### Key Resources
- `src/core_compute/engineering/run_pipeline.py`
- `docs/app/HEaC_opensource_Meep.md` (HEaC details)
- `docs/app/THERMAL_AND_PARASITICS.md`
- `src/core_compute/engineering/ci_baseline/` (tape-out baselines)

---

## 3. Backend/API Developer
**Model:** `openchat` (code and API design)  
**Role:** Manage control plane and async orchestration

### Expertise
- FastAPI REST API design
- Celery task queuing and workers
- Redis caching and message broker
- Hybrid compute dispatcher
- Task registry and job routing
- Async/streaming APIs

### Responsibilities
- Implement/maintain FastAPI endpoints
- Design Celery tasks for pipeline/protocol execution
- Route jobs to compute resources (Local, IBM QPU, EKS)
- Implement task streaming and live logs
- Handle error recovery and retry logic

### Example Tasks
- "Design API endpoint for submitting a circuit to IBM Quantum"
- "How do we stream pipeline progress to the frontend in real-time?"
- "What Celery tasks are needed for the full tape-out flow?"

### Key Resources
- `src/backend/main.py` (FastAPI app)
- `src/backend/dispatcher.py` (compute routing)
- `src/backend/task_registry.py` (task types)
- `src/backend/executor.py` (local execution)

---

## 4. Frontend Developer
**Model:** `openchat` (React/TypeScript)  
**Role:** Build user interfaces

### Expertise
- React and Vite SPA development
- TypeScript/JavaScript build and tooling
- UI component design and styling
- WebSocket streaming for live updates
- REST API integration

### Responsibilities
- Implement React pages (Run Pipeline, Workflows, Deploy)
- Build drag-and-drop flow editors
- Display live task logs via WebSocket
- Create responsive UI for complex workflows
- Integrate with FastAPI backend

### Example Tasks
- "Create a circuit selector UI for Run Pipeline page"
- "Implement drag-drop workflow builder for task DAGs"
- "How do we display streaming logs as tasks run?"

### Key Resources
- `src/frontend/` (React SPA)
- `src/frontend/README.md` (frontend docs)
- Package: `src/frontend/package.json`

---

## 5. Infrastructure/DevOps Expert
**Model:** `mistral` (infrastructure reasoning)  
**Role:** Deployment and operations

### Expertise
- Docker and Docker Compose containerization
- Kubernetes/Helm deployment and scaling
- OpenTofu infrastructure-as-code provisioning
- Multi-cloud support (AWS, GCP, Azure, OpenNebula)
- CI/CD pipeline automation
- Container security scanning (Trivy)

### Responsibilities
- Manage Docker images and compose configurations
- Deploy to Kubernetes with Helm charts
- Provision cloud infrastructure with OpenTofu
- Maintain CI/CD workflows and health checks
- Monitor and scale services

### Example Tasks
- "Update Helm chart to scale workers to 10 replicas"
- "Add Trivy container scanning to the CI pipeline"
- "Deploy to AWS EKS with RDS PostgreSQL backend"

### Key Resources
- `platform/deploy/` (Helm chart, deploy docs)
- `platform/infra/tofu/` (OpenTofu configs)
- `docker-compose.yml`, `docker-compose.full.yml`
- `.github/workflows/hardware-ci.yml` (CI pipeline)

---

## 6. Documentation/Knowledge Manager
**Model:** `neural-chat` (writing and comprehensiveness)  
**Role:** Maintain knowledge base

### Expertise
- Technical writing and documentation
- Architecture diagrams and design docs
- API documentation and examples
- Whitepaper and research paper writing
- Roadmap and action item management

### Responsibilities
- Write and update docs/ (user guides, API)
- Maintain research/ whitepapers and LaTeX sources
- Document architecture decisions and rationale
- Keep ROADMAP_SCHEDULE and PROGRAM_ACTION_ITEMS current
- Manage docs/app/ALPHA_SCOPE and CUSTOMER focus

### Example Tasks
- "Document the updated pipeline architecture"
- "Write API docs for the new workflow submission endpoint"
- "Update ROADMAP for next quarter"

### Key Resources
- `docs/app/README.md` (doc index)
- `docs/research/` (whitepapers and LaTeX)
- `docs/app/ALPHA_SCOPE.md`, `PROGRAM_ACTION_ITEMS.md`
- `README.md` (project overview)

---

## 7. QA/Testing Specialist
**Model:** `openchat` (testing framework knowledge)  
**Role:** Quality assurance and test coverage

### Expertise
- Pytest framework and test design
- Unit, integration, and end-to-end testing
- CI baseline management and regression detection
- Coverage metrics and reporting
- Test automation in CI/CD

### Responsibilities
- Design and implement test suite
- Maintain CI baselines (GDS manifests, outputs)
- Detect and report regressions
- Ensure test coverage targets met
- Debug failing tests in CI

### Example Tasks
- "Design tests for the inverse design convergence"
- "Set up baseline for GDS output diffs"
- "Why are we seeing DRC violations in CI?"

### Key Resources
- `tests/` (pytest suite)
- `src/core_compute/engineering/ci_baseline/` (baselines)
- `requirements-test.txt` (test dependencies)
- `.github/workflows/hardware-ci.yml` (CI test execution)

---

## 8. Project Manager/Coordinator
**Model:** `neural-chat` (coordination and summarization)  
**Role:** Orchestrate committee and track progress

### Expertise
- Project planning and task prioritization
- Cross-agent coordination and communication
- Risk identification and mitigation
- Progress tracking and status reporting
- AI committee session orchestration

### Responsibilities
- Coordinate agent queries and discussions
- Route tasks to appropriate agents
- Track milestones and deliverables
- Identify blockers and risks
- Generate status reports
- Document committee decisions

### Example Tasks
- "Which agents should review this new feature?"
- "What's our status on the Alpha tape-out?"
- "We're 20% over schedule. What are our options?"

### Key Resources
- `docs/app/ALPHA_SCOPE.md` (Alpha scope)
- `docs/app/ROADMAP_SCHEDULE.md` (timeline)
- `docs/app/PROGRAM_ACTION_ITEMS.md` (tasks)
- `README.md` (project vision)

---

## Committee Communication Patterns

### 1. **Brainstorm** (All agents)
Get diverse perspectives on a strategic question.

```python
results = orchestrator.brainstorm_committee(
    "What are the top 3 risks for next quarter?"
)
```

### 2. **Route Task** (PM-coordinated)
PM decides which agents to consult, then queries them.

```python
results = orchestrator.route_task(
    "Add FDTD support to the inverse design step"
)
```

### 3. **Direct Query** (Role-specific)
Ask a specific agent for expertise.

```python
result = orchestrator.query_agent(
    AgentRole.ENGINEERING_PIPELINE,
    "Design thermal management for the HEaC stage"
)
```

### 4. **Milestone Review** (PM + all)
PM summarizes progress, each agent reports status.

---

## Recommended Model Pulls

Ensure Ollama has these models pulled locally:

```bash
ollama pull neural-chat      # Fast, good at writing
ollama pull mistral          # Strong reasoning
ollama pull openchat         # Good at code/APIs
```

Optional: Pull larger models for complex reasoning
```bash
ollama pull llama2           # General purpose
ollama pull dolphin-mixtral  # Strong at planning
```

---

## Next Steps

1. **Pull required models** (see above)
2. **Verify Ollama connection**: `orchestrator._verify_ollama_connection()`
3. **Test committee**: Run `python orchestrator.py` to see roster
4. **Query agents** on QASIC tasks
5. **Integrate with VS Code** for IDE-based committee access
6. **Automate workflows** for recurring tasks (CI reviews, merge gates, etc.)

---

## Notes

- Each agent respects ALPHA_SCOPE.md constraints
- Model choices balance speed (neural-chat) vs reasoning (mistral)
- Customize system prompts in `orchestrator.py` for your specific needs
- All agents have context about the 3-qubit ASIC topology and metasurface pipeline
- Committee decisions are logged and traceable

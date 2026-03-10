"""
QASIC AI Committee Orchestrator
Coordinates multi-agent Ollama committee for collaborative execution of QASIC vision
"""

import os
import json
import requests
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class AgentRole(Enum):
    """Committee member roles"""
    QUANTUM_PROTOCOL = "quantum-protocol-specialist"
    ENGINEERING_PIPELINE = "engineering-pipeline-expert"
    BACKEND_API = "backend-api-developer"
    FRONTEND = "frontend-developer"
    INFRASTRUCTURE = "infrastructure-devops"
    DOCUMENTATION = "documentation-manager"
    QA_TESTING = "qa-testing-specialist"
    PROJECT_MANAGER = "project-manager-coordinator"


@dataclass
class AgentProfile:
    """Agent role profile with model assignment"""
    role: AgentRole
    model: str
    description: str
    expertise: List[str]
    system_prompt: str


class CommitteeOrchestrator:
    """Main committee coordinator for QASIC project"""

    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.agents: Dict[AgentRole, AgentProfile] = self._initialize_agents()
        self._verify_ollama_connection()

    def _initialize_agents(self) -> Dict[AgentRole, AgentProfile]:
        """Initialize committee members with role specs"""
        agents = {}

        agents[AgentRole.QUANTUM_PROTOCOL] = AgentProfile(
            role=AgentRole.QUANTUM_PROTOCOL,
            model="neural-chat",  # Fast, good at protocols
            description="Quantum Protocol Specialist",
            expertise=[
                "Quantum protocols (entanglement, teleportation, QKD)",
                "BB84, E91, bit commitment schemes",
                "3-qubit ASIC topology and gates",
                "Error correction and channel noise",
                "Protocol design and verification",
            ],
            system_prompt="""You are a Quantum Protocol Specialist for QASIC Engineering-as-Code.
Your expertise: quantum entanglement, teleportation, QKD protocols, bit commitment, 
error correction, and the 3-qubit linear chain ASIC.

Focus on protocol correctness, circuit design, and quantum state management.
Reference demos/ and docs/app/QUANTUM_ASIC.md for ASIC specs.
When designing circuits, ensure compatibility with the linear chain topology: 0—1—2""",
        )

        agents[AgentRole.ENGINEERING_PIPELINE] = AgentProfile(
            role=AgentRole.ENGINEERING_PIPELINE,
            model="mistral",  # Strong reasoning for engineering
            description="Engineering Pipeline Expert",
            expertise=[
                "Metasurface routing and design",
                "Inverse design and optimization",
                "HEaC (Hybrid EM Analysis and Calibration)",
                "GDS generation and layout",
                "DRC/LVS verification",
            ],
            system_prompt="""You are an Engineering Pipeline Expert for QASIC.
Expertise: metasurface routing, inverse design, HEaC, GDS, DRC/LVS.

Your responsibility: guide the engineering pipeline (routing → inverse design → HEaC → GDS → DRC/LVS).
Reference src/core_compute/engineering/ and docs/app/HEaC_opensource_Meep.md.
Coordinate thermal, parasitic, and calibration flows.
Ensure tape-out readiness with --heac --gds --drc --lvs flags.""",
        )

        agents[AgentRole.BACKEND_API] = AgentProfile(
            role=AgentRole.BACKEND_API,
            model="openchat",  # Good at code and APIs
            description="Backend/API Developer",
            expertise=[
                "FastAPI application design",
                "Celery task orchestration",
                "Hybrid compute dispatcher",
                "Task registry and job execution",
                "REST API and async streaming",
            ],
            system_prompt="""You are a Backend/API Developer for QASIC.
Expertise: FastAPI, Celery, Redis, async job dispatch, REST APIs.

Your responsibility: maintain the control plane (API, Celery workers, dispatcher).
Reference src/backend/main.py, dispatcher.py, and task_registry.
Guide task enqueuing, job routing to compute resources (Local, IBM QPU, EKS).
Ensure async task streaming and proper error handling.""",
        )

        agents[AgentRole.FRONTEND] = AgentProfile(
            role=AgentRole.FRONTEND,
            model="openchat",
            description="Frontend Developer",
            expertise=[
                "React and Vite SPA development",
                "UI for Run Pipeline, Workflows, Deploy pages",
                "Drag-and-drop flow-based workflows",
                "WebSocket streaming for live task logs",
                "Integration with FastAPI backend",
            ],
            system_prompt="""You are a Frontend Developer for QASIC.
Expertise: React, Vite, TypeScript/JavaScript, WebSocket streaming, UI/UX.

Your responsibility: frontend SPA for workflows, pipeline runs, and deployment.
Reference src/frontend/ and relevant React components.
Guide UI for Run Pipeline (project + circuit selection, full pipeline execution),
Workflows (drag-drop DAG builders), and Deploy (target selection, generated commands).
Ensure real-time task log streaming and responsive design.""",
        )

        agents[AgentRole.INFRASTRUCTURE] = AgentProfile(
            role=AgentRole.INFRASTRUCTURE,
            model="mistral",  # Strong at infrastructure reasoning
            description="Infrastructure/DevOps Expert",
            expertise=[
                "Docker and Docker Compose",
                "Kubernetes/Helm deployment",
                "OpenTofu infrastructure-as-code",
                "Cloud deployment (AWS, GCP, Azure, OpenNebula)",
                "CI/CD pipelines and hardware CI",
            ],
            system_prompt="""You are an Infrastructure/DevOps Expert for QASIC.
Expertise: Docker, Kubernetes, Helm, OpenTofu, AWS/GCP/Azure.

Your responsibility: deployment, scaling, and infrastructure automation.
Reference platform/deploy/, platform/infra/tofu/, and .github/workflows/.
Guide Helm chart configuration, OpenTofu provisioning, Docker image optimization.
Ensure CI/CD pipeline integrity (hardware-ci.yml, container scanning, ECR push).""",
        )

        agents[AgentRole.DOCUMENTATION] = AgentProfile(
            role=AgentRole.DOCUMENTATION,
            model="neural-chat",  # Good at writing and comprehensiveness
            description="Documentation/Knowledge Manager",
            expertise=[
                "Technical documentation and whitepapers",
                "API documentation and examples",
                "Architecture diagrams and design decisions",
                "Roadmap and action items",
                "Knowledge base and wiki maintenance",
            ],
            system_prompt="""You are a Documentation/Knowledge Manager for QASIC.
Expertise: technical writing, architecture documentation, roadmap management.

Your responsibility: maintain docs/, whitepapers, API schemas, design rationale.
Reference docs/app/README.md (index), docs/research/ (whitepapers), and inline code docs.
Guide architecture_overview, ORCHESTRATION, deployment guides, and research papers.
Keep ROADMAP_SCHEDULE, PROGRAM_ACTION_ITEMS, and ALPHA_SCOPE updated.""",
        )

        agents[AgentRole.QA_TESTING] = AgentProfile(
            role=AgentRole.QA_TESTING,
            model="openchat",
            description="QA/Testing Specialist",
            expertise=[
                "Pytest framework and test design",
                "Unit, integration, and e2e testing",
                "CI baseline management and diffs",
                "Regression testing",
                "Test coverage and quality metrics",
            ],
            system_prompt="""You are a QA/Testing Specialist for QASIC.
Expertise: pytest, test design, CI baselines, coverage metrics.

Your responsibility: test suite, CI/CD testing, and quality assurance.
Reference tests/, src/core_compute/engineering/ci_baseline/, requirements-test.txt.
Guide test design for protocols, engineering pipeline, backend, and frontend.
Ensure baseline diffs track GDS/manifest changes and regressions.""",
        )

        agents[AgentRole.PROJECT_MANAGER] = AgentProfile(
            role=AgentRole.PROJECT_MANAGER,
            model="neural-chat",  # Good at coordination and summaries
            description="Project Manager/Coordinator",
            expertise=[
                "Project planning and task prioritization",
                "Cross-team coordination",
                "Progress tracking and status reporting",
                "Risk identification and mitigation",
                "AI committee session orchestration",
            ],
            system_prompt="""You are a Project Manager/Coordinator for QASIC.
Expertise: planning, coordination, risk management, status reporting.

Your responsibility: orchestrate committee, track milestones, report progress.
Reference docs/app/ALPHA_SCOPE.md, ROADMAP_SCHEDULE, PROGRAM_ACTION_ITEMS.
Guide task breakdown, dependency tracking, and cross-team communication.
Ensure committee decisions are documented and aligned with Alpha vision.""",
        )

        return agents

    def _verify_ollama_connection(self):
        """Verify connection to Ollama server"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("✓ Connected to Ollama at %s", self.base_url)
            else:
                logger.warning("⚠ Ollama connection status: %d", response.status_code)
        except Exception as e:
            logger.error("✗ Cannot connect to Ollama: %s", e)
            logger.info("Start Ollama with: ollama serve")

    def query_agent(
        self,
        role: AgentRole,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Query a specific agent with a task"""
        agent = self.agents[role]
        logger.info("→ Querying %s: %s...", agent.description, task[:50])

        system_prompt = agent.system_prompt
        if context:
            system_prompt += f"\n\nContext: {json.dumps(context, indent=2)}"

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": agent.model,
                    "prompt": task,
                    "system": system_prompt,
                    "stream": False,
                },
                timeout=120,
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "No response")
            else:
                logger.error(
                    "Agent query failed: %d - %s", response.status_code, response.text
                )
                return f"Error: {response.status_code}"
        except Exception as e:
            logger.error("Exception querying agent: %s", e)
            return f"Exception: {str(e)}"

    def brainstorm_committee(self, topic: str) -> Dict[str, str]:
        """Get input from all committee members on a topic"""
        logger.info("🏛️ Committee brainstorm: %s", topic)
        results = {}
        for role, agent in self.agents.items():
            results[role.value] = self.query_agent(role, topic)
        return results

    def route_task(self, task: str, context: Optional[Dict] = None) -> Dict[str, str]:
        """Let the PM determine which agents should handle a task"""
        routing_task = f"""Given this task, which committee members (roles) should be consulted?
Task: {task}
Respond with a JSON dict: {{"roles": ["role1", "role2", ...], "rationale": "..."}}"""

        pm_response = self.query_agent(
            AgentRole.PROJECT_MANAGER, routing_task, context
        )
        logger.info("PM routing: %s", pm_response[:200])

        # Execute task with routed agents
        try:
            routing = json.loads(pm_response)
            roles_to_query = routing.get("roles", [])
        except:
            logger.warning("Could not parse PM routing, querying all agents")
            roles_to_query = [r.value for r in self.agents.keys()]

        results = {}
        for role_name in roles_to_query:
            role = next(
                (r for r in self.agents if r.value == role_name),
                AgentRole.PROJECT_MANAGER,
            )
            results[role_name] = self.query_agent(role, task, context)
        return results

    def summarize_progress(self, milestone: str) -> str:
        """Get PM summary of milestone progress"""
        summary_task = f"Summarize progress for milestone: {milestone}. What's done, in progress, at risk?"
        return self.query_agent(AgentRole.PROJECT_MANAGER, summary_task)

    def list_agents(self) -> str:
        """Print committee roster"""
        roster = "\n🏛️ QASIC AI Committee Roster:\n"
        for role, agent in self.agents.items():
            roster += f"\n  • {agent.description} ({agent.model})\n"
            roster += f"    Expertise: {', '.join(agent.expertise[:2])}\n"
        return roster


# Example usage
if __name__ == "__main__":
    orchestrator = CommitteeOrchestrator()
    print(orchestrator.list_agents())

    # Example: Query quantum specialist
    # result = orchestrator.query_agent(
    #     AgentRole.QUANTUM_PROTOCOL,
    #     "Design a Bell pair preparation circuit for the 3-qubit linear chain"
    # )
    # print(f"Quantum Specialist: {result}")

    # Example: Route a complex task
    # results = orchestrator.route_task(
    #     "We need to add thermal analysis to the metasurface pipeline. How should we proceed?"
    # )
    # for role, response in results.items():
    #     print(f"\n{role}:\n{response}\n")

# VS Code Integration for QASIC AI Committee

Guide to integrate the AI committee into VS Code for seamless IDE-based access.

---

## Method 1: Custom Commands in VS Code

### Step 1: Create Command Scripts

Create `ai-committee/scripts/query-committee.ps1`:

```powershell
param(
    [string]$query = $(Read-Host "Enter your question"),
    [string]$agent = "all"  # "all", "quantum", "engineering", etc.
)

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)

cd "$repoRoot\ai-committee"

if ($agent -eq "all") {
    python -c "
from orchestrator import CommitteeOrchestrator
orch = CommitteeOrchestrator()
results = orch.route_task('$query')
for role, response in results.items():
    print(f'\n{role}:\n{response}\n')
"
} else {
    python -c "
from orchestrator import CommitteeOrchestrator, AgentRole
orch = CommitteeOrchestrator()
roles = {
    'quantum': AgentRole.QUANTUM_PROTOCOL,
    'engineering': AgentRole.ENGINEERING_PIPELINE,
    'backend': AgentRole.BACKEND_API,
    'frontend': AgentRole.FRONTEND,
    'infra': AgentRole.INFRASTRUCTURE,
    'docs': AgentRole.DOCUMENTATION,
    'qa': AgentRole.QA_TESTING,
    'pm': AgentRole.PROJECT_MANAGER,
}
role = roles.get('$agent', AgentRole.PROJECT_MANAGER)
result = orch.query_agent(role, '$query')
print(result)
"
}
```

### Step 2: Add VS Code Tasks

Add to `.vscode/tasks.json`:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Query QASIC Committee",
            "type": "shell",
            "command": "powershell",
            "args": [
                "-ExecutionPolicy", "Bypass",
                "-File", "${workspaceFolder}/ai-committee/scripts/query-committee.ps1"
            ],
            "problemMatcher": [],
            "presentation": {
                "echo": true,
                "reveal": "always",
                "panel": "shared"
            },
            "group": {
                "kind": "test",
                "isDefault": false
            }
        },
        {
            "label": "Quantum Protocol Specialist",
            "type": "shell",
            "command": "powershell",
            "args": [
                "-ExecutionPolicy", "Bypass",
                "-File", "${workspaceFolder}/ai-committee/scripts/query-committee.ps1",
                "-agent", "quantum"
            ],
            "problemMatcher": [],
            "presentation": {
                "reveal": "always",
                "panel": "shared"
            }
        },
        {
            "label": "Engineering Pipeline Expert",
            "type": "shell",
            "command": "powershell",
            "args": [
                "-ExecutionPolicy", "Bypass",
                "-File", "${workspaceFolder}/ai-committee/scripts/query-committee.ps1",
                "-agent", "engineering"
            ],
            "problemMatcher": [],
            "presentation": {
                "reveal": "always",
                "panel": "shared"
            }
        }
    ]
}
```

### Step 3: Bind to Keyboard Shortcuts

Add to `.vscode/keybindings.json`:

```json
[
    {
        "key": "ctrl+shift+q",
        "command": "workbench.action.tasks.runTask",
        "args": "Query QASIC Committee"
    },
    {
        "key": "ctrl+shift+alt+p",
        "command": "workbench.action.tasks.runTask",
        "args": "Quantum Protocol Specialist"
    },
    {
        "key": "ctrl+shift+alt+e",
        "command": "workbench.action.tasks.runTask",
        "args": "Engineering Pipeline Expert"
    }
]
```

---

## Method 2: VS Code Extension (Advanced)

### Create Extension Structure

```
qasic-committee-ext/
├── src/
│   └── extension.ts
├── package.json
├── tsconfig.json
└── README.md
```

### `package.json`

```json
{
    "name": "qasic-committee",
    "displayName": "QASIC AI Committee",
    "description": "Query the QASIC AI committee for expert guidance",
    "version": "0.1.0",
    "engines": {
        "vscode": "^1.60.0"
    },
    "categories": ["Other"],
    "activationEvents": [
        "onCommand:qasic-committee.query",
        "onCommand:qasic-committee.queryQuantum",
        "onCommand:qasic-committee.queryEngineering",
        "onCommand:qasic-committee.brainstorm"
    ],
    "main": "./dist/extension.js",
    "contributes": {
        "commands": [
            {
                "command": "qasic-committee.query",
                "title": "QASIC: Query Committee"
            },
            {
                "command": "qasic-committee.queryQuantum",
                "title": "QASIC: Ask Quantum Specialist"
            },
            {
                "command": "qasic-committee.queryEngineering",
                "title": "QASIC: Ask Engineering Expert"
            },
            {
                "command": "qasic-committee.brainstorm",
                "title": "QASIC: Brainstorm (All Agents)"
            }
        ],
        "keybindings": [
            {
                "command": "qasic-committee.query",
                "key": "ctrl+shift+q",
                "when": "editorFocus"
            }
        ]
    },
    "scripts": {
        "compile": "tsc -p ./",
        "watch": "tsc -watch -p ./",
        "pretest": "npm run compile",
        "test": "node ./out/test/runTest.js"
    },
    "devDependencies": {
        "@types/vscode": "^1.60.0",
        "@types/node": "^16.0.0",
        "typescript": "^4.3.0"
    },
    "dependencies": {}
}
```

### `src/extension.ts`

```typescript
import * as vscode from 'vscode';
import * as path from 'path';
import { spawn } from 'child_process';

export function activate(context: vscode.ExtensionContext) {
    
    const queryCommand = vscode.commands.registerCommand(
        'qasic-committee.query',
        async () => {
            const query = await vscode.window.showInputBox({
                prompt: 'Ask the QASIC Committee',
                placeHolder: 'e.g., Design a Bell pair circuit (pipeline supports any qubit count)'
            });
            
            if (!query) return;
            
            const output = vscode.window.createOutputChannel('QASIC Committee');
            output.show();
            output.append(`\n📌 Query: ${query}\n`);
            output.append(`${'='.repeat(60)}\n`);
            
            queryCommittee(query, 'all', output);
        }
    );
    
    const quantumCommand = vscode.commands.registerCommand(
        'qasic-committee.queryQuantum',
        async () => {
            const query = await vscode.window.showInputBox({
                prompt: 'Ask Quantum Protocol Specialist',
                placeHolder: 'Quantum protocol question...'
            });
            
            if (!query) return;
            
            const output = vscode.window.createOutputChannel('QASIC Committee');
            output.show();
            output.append(`\n🔬 Quantum Specialist: ${query}\n`);
            output.append(`${'='.repeat(60)}\n`);
            
            queryCommittee(query, 'quantum', output);
        }
    );
    
    context.subscriptions.push(queryCommand);
    context.subscriptions.push(quantumCommand);
}

function queryCommittee(
    query: string,
    agent: string,
    output: vscode.OutputChannel
) {
    const repoRoot = vscode.workspace.workspaceFolders?.[0].uri.fsPath;
    if (!repoRoot) {
        output.append('Error: No workspace folder open\n');
        return;
    }
    
    const pythonScript = path.join(repoRoot, 'ai-committee', 'orchestrator.py');
    
    const python = spawn('python', [
        '-c',
        `
from orchestrator import CommitteeOrchestrator, AgentRole
import sys
sys.path.insert(0, '${path.join(repoRoot, 'ai-committee')}')
orch = CommitteeOrchestrator()
if '${agent}' == 'all':
    results = orch.route_task('${query}')
    for role, response in results.items():
        print(f'\\n{role}:\\n{response}\\n')
else:
    agents = {
        'quantum': AgentRole.QUANTUM_PROTOCOL,
        'engineering': AgentRole.ENGINEERING_PIPELINE,
    }
    role = agents.get('${agent}')
    if role:
        result = orch.query_agent(role, '${query}')
        print(result)
`
    ]);
    
    python.stdout?.on('data', (data) => {
        output.append(data.toString());
    });
    
    python.stderr?.on('data', (data) => {
        output.append(`\nError: ${data.toString()}\n`);
    });
    
    python.on('close', (code) => {
        output.append(`\n${'='.repeat(60)}\n✓ Complete\n`);
    });
}

export function deactivate() {}
```

---

## Method 3: Jupyter Notebook Interface

### Create Interactive Notebook

`ai-committee/notebooks/committee-meeting.ipynb`:

```json
{
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# QASIC AI Committee Meeting\n",
                "\n",
                "Interactive committee session for collaborative decision-making"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": null,
            "metadata": {},
            "outputs": [],
            "source": [
                "import sys\n",
                "sys.path.insert(0, '..')\n",
                "\n",
                "from orchestrator import CommitteeOrchestrator, AgentRole\n",
                "import json\n",
                "\n",
                "orch = CommitteeOrchestrator()\n",
                "print(orch.list_agents())"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Query Specific Agent"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": null,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Edit the question below and run\n",
                "result = orch.query_agent(\n",
                "    AgentRole.QUANTUM_PROTOCOL,\n",
                "    \"Design a Bell pair preparation circuit (e.g. reference 3-qubit linear chain)\"\n",
                ")\n",
                "print(result)"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Committee Brainstorm"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": null,
            "metadata": {},
            "outputs": [],
            "source": [
                "results = orch.brainstorm_committee(\n",
                "    \"What are the top 3 risks for Alpha launch?\"\n",
                ")\n",
                "\n",
                "for role, response in results.items():\n",
                "    print(f\"\\n{'='*60}\")\n",
                "    print(f\"📌 {role}\")\n",
                "    print(f\"{'='*60}\")\n",
                "    print(response)"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}
```

### Open in VS Code

1. Install **Jupyter** extension (ms-toolsai.jupyter)
2. Open `ai-committee/notebooks/committee-meeting.ipynb`
3. Select Python kernel
4. Run cells interactively

---

## Quick Integration Checklist

- [ ] Create `ai-committee/scripts/query-committee.ps1`
- [ ] Add tasks to `.vscode/tasks.json`
- [ ] Add keybindings to `.vscode/keybindings.json`
- [ ] Test with `Ctrl+Shift+Q`
- [ ] (Optional) Create Jupyter notebook
- [ ] (Advanced) Build VS Code extension

---

## Using the Integration

### Via Command Palette
1. `Ctrl+Shift+P`
2. Type: "QASIC Query"
3. Enter your question

### Via Keyboard
- `Ctrl+Shift+Q`: Query full committee
- `Ctrl+Shift+Alt+P`: Query quantum specialist
- `Ctrl+Shift+Alt+E`: Query engineering expert

### Via Notebook
1. Open `ai-committee/notebooks/committee-meeting.ipynb`
2. Edit cell and run with `Shift+Enter`
3. See results inline

---

## Next Steps

1. Implement **Method 1** (tasks + shortcuts) - fastest setup
2. Test with sample queries
3. Add more agent shortcuts as needed
4. (Optional) Build full **Method 2** extension for package sharing
5. Use **Method 3** (Jupyter) for analysis and documentation

---

**Recommendation:** Start with Method 1, then add Jupyter notebook (Method 3) for collaborative sessions.

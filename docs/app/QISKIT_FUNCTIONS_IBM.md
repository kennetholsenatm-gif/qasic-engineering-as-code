# Run on IBM and Qiskit Functions

The app can run circuits and protocols on **IBM Quantum** (sim or hardware) via the existing pipeline and protocol job flow. You can extend this with **Qiskit Functions** for better error mitigation and workload visibility.

## Current behavior

- **Run Pipeline** and **Protocol** flows submit jobs to IBM Quantum (or simulator) and poll status via WebSocket. See [OPENQASM_TO_ASIC_PIPELINE.md](OPENQASM_TO_ASIC_PIPELINE.md) and `src/core_compute/engineering/run_protocol_on_ibm.py`.
- When using a Qiskit Function (see below), job results may include a **workload summary** in `job.result()['metadata']['resource_usage']` (CPU/GPU/QPU time per stage), which the app can surface in the UI.

## Using a circuit function from the app

When running a protocol on **IBM hardware**, the **Run protocol** page offers an option **Use Qiskit Circuit Function**. When enabled, the app tries to submit the protocol circuit via the [Qiskit Functions Catalog](https://www.ibm.com/quantum/blog/functions-2026) (circuit function) for error mitigation and workload summaries. If the catalog is not installed (`qiskit-ibm-catalog`) or submission fails, the app falls back to the standard IBM Sampler path. Install the optional extra with `pip install -e ".[ibm-functions]"`. You can set `QISKIT_CIRCUIT_FUNCTION_ID` in the environment to choose which catalog function to use (default is `ibm/circuit-function`).

## Extending with Qiskit Functions

[Qiskit Functions](https://www.ibm.com/quantum/blog/functions-2026) provide:

- **Circuit functions**: Submit your compiled/transpiled circuit; the function handles transpilation, error suppression/mitigation, and execution with tunable time vs accuracy trade-offs. Useful for “run this ASIC-style circuit on IBM” with better optimization than a raw Sampler run.
- **Application functions**: Submit a classical problem (e.g. QUBO, chemistry); the function maps it to circuits and runs at scale. Relevant if you add “solve this optimization/chemistry problem” flows that delegate to IBM.
- **Workload summary**: For jobs run via Qiskit Functions, `result['metadata']['resource_usage']` exposes CPU/QPU time per stage (e.g. `RUNNING: OPTIMIZING_FOR_HARDWARE`, `RUNNING: EXECUTING_QPU`), so you can show users classical vs quantum cost.

Premium and Flex Plan users can request free trials from the [Qiskit Functions Catalog](https://www.ibm.com/quantum/blog/functions-2026); eligible Premium organizations can request a free one-year license (see the blog for dates and contacts).

## References

- [Qiskit Functions updates accelerate research for the year of quantum advantage](https://www.ibm.com/quantum/blog/functions-2026) (IBM Quantum Blog, Feb 2026).

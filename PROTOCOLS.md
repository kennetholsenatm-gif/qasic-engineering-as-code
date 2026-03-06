# Toy Protocol Descriptions

## 1. Entanglement and teleportation

- **Bell pair:** \(| \Phi^+ \rangle = (|00\rangle + |11\rangle)/\sqrt{2}\). Created by H on qubit 0, then CNOT(0,1).
- **Distribution (conceptual):** A source (e.g. in space) sends one photon to Alice, one to Bob. In code we just create the state.
- **Teleportation:** Alice has an unknown state \(|\psi\rangle\) and shares a Bell pair with Bob. She runs CNOT(msg, her half), H(msg), then measures both; she sends the 2-bit outcome to Bob. Bob applies \(X^{m_2} Z^{m_1}\) to his qubit and holds \(|\psi\rangle\). No cloning: the original at Alice is destroyed.

## 2. Tamper-evidence (Thief)

- **Idea:** If an adversary disturbs the quantum channel (e.g. applies a rotation to Bob’s qubit before he uses it), the state Bob receives is no longer \(|\psi\rangle\).
- **Model:** After the teleport circuit we apply \(R_x(\theta)\) to Bob’s qubit (the “Thief” action), then compute the fidelity of Bob’s reduced state to \(|\psi\rangle\). Fidelity drops below 1; the drop is detectable.
- **Takeaway:** Interference leaves a statistical fingerprint; quantum links are intrinsically tamper-evident compared to classical.

## 3. Toy bit commitment

- **Setup:** Bob creates a Bell pair and sends one half to Alice (quantum modem picture).
- **Commit:** Alice commits to bit \(b\). She either leaves her half as is (\(b=0\)) or applies \(X\) (\(b=1\)), then measures in the \(Z\) basis and gets outcome \(m\). She stores \((b, m)\).
- **Open:** Alice sends \((b, m)\) to Bob. Bob measures his qubit in \(Z\); outcome should match \(m\) (Bell correlation). He checks consistency.
- **Security (toy):** *Hiding:* Before open, Bob’s reduced state is \(I/2\), so he gets no information about \(b\). *Binding:* Alice has already measured; we assume she does not keep a quantum copy, so she cannot change \(b\) without being inconsistent. This is **not** unconditionally secure (Mayers–Lo–Chau no-go); we assume passive adversary / no quantum storage.

## Where this connects to “space + quantum modems”

- **Entanglement from space:** Source on a satellite creates pairs and sends one photon to each ground station (laser link). Same idea as `create_bell_pair` / `distribute_pairs`, with a real channel.
- **Bit commitment on top:** Use the same quantum link to establish shared entanglement, then run the toy commitment (or a more refined variant with explicit security assumptions). The link’s tamper-evidence supports the story.

"""Quantum RNG and security token generator."""
import os
import hashlib
import binascii
import math
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

# Try to import IBM Runtime for real quantum hardware execution
try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    IBM_RUNTIME_AVAILABLE = True
except ImportError:
    IBM_RUNTIME_AVAILABLE = False


class QuantumRNG:
    def __init__(self, use_real_hardware: bool = False, ibm_token: str = None):
        """
        Initializes the Quantum RNG.
        
        :param use_real_hardware: If True, connects to IBM Quantum hardware. 
                                  If False, uses a local quantum simulator.
        :param ibm_token: Your IBM Quantum API token (required if use_real_hardware is True).
        """
        self.use_real_hardware = use_real_hardware
        
        if self.use_real_hardware:
            if not IBM_RUNTIME_AVAILABLE:
                raise ImportError("qiskit-ibm-runtime is not installed. Please run: pip install qiskit-ibm-runtime")
            if not ibm_token:
                raise ValueError("An IBM Quantum API token must be provided to use real hardware.")
            
            print("Authenticating with IBM Quantum...")
            self.service = QiskitRuntimeService(channel="ibm_quantum_platform", token=ibm_token)
            
            # Select the least busy quantum computer automatically
            print("Finding the least busy quantum backend...")
            self.backend = self.service.least_busy(simulator=False, operational=True)
            print(f"Selected Backend: {self.backend.name}")
        else:
            print("Using local quantum Statevector Simulator.")
            self.backend = None

    def generate_raw_bits(self, min_bits: int) -> str:
        """
        Generates raw quantum bits by measuring qubits in superposition.
        """
        # We use a 16-qubit circuit. You can scale this up depending on the hardware.
        num_qubits = 16
        
        # Calculate how many shots we need. We ask for extra to account for 
        # the bits discarded by the Von Neumann extractor.
        shots = math.ceil((min_bits * 4) / num_qubits) 
        
        # 1. Build the Quantum Circuit
        qc = QuantumCircuit(num_qubits)
        qc.h(range(num_qubits)) # Apply Hadamard gates to put qubits in 50/50 superposition
        qc.measure_all()        # Measure the collapsed quantum states
        
        raw_bitstream = ""
        
        if self.use_real_hardware:
            # Transpile circuit for the specific IBM quantum chip architecture
            pm = generate_preset_pass_manager(backend=self.backend, optimization_level=1)
            isa_circuit = pm.run(qc)
            
            # Run using the V2 Sampler primitive
            sampler = SamplerV2(self.backend)
            print(f"Executing quantum circuit on {self.backend.name} (Shots: {shots})...")
            job = sampler.run([isa_circuit], shots=shots)
            result = job.result()
            
            # Extract bitstrings from the V2 primitive result
            bitstrings = result[0].data.meas.get_bitstrings()
            raw_bitstream = "".join(bitstrings)
            
        else:
            # Run using local simulator
            sampler = StatevectorSampler()
            job = sampler.run([qc], shots=shots)
            result = job.result()
            
            # Extract bitstrings
            bitstrings = result[0].data.meas.get_bitstrings()
            raw_bitstream = "".join(bitstrings)
            
        return raw_bitstream

    def von_neumann_extractor(self, raw_bits: str) -> str:
        """
        Debiasing algorithm for hardware True Random Number Generators (TRNGs).
        Reads bits in pairs:
        - '01' becomes '0'
        - '10' becomes '1'
        - '00' and '11' are discarded to remove hardware bias
        """
        extracted = []
        for i in range(0, len(raw_bits) - 1, 2):
            pair = raw_bits[i:i+2]
            if pair == '01':
                extracted.append('0')
            elif pair == '10':
                extracted.append('1')
        return "".join(extracted)

    def generate_security_token(self, num_bytes: int = 32) -> str:
        """
        Generates a secure, cryptographically safe token using quantum entropy.
        
        :param num_bytes: Length of the desired token in bytes.
        :return: A hexadecimal string representing the security token.
        """
        target_bits = num_bytes * 8
        unbiased_bits = ""
        
        print(f"Generating at least {target_bits} bits of quantum entropy...")
        
        # Loop until we have enough unbiased bits
        while len(unbiased_bits) < target_bits:
            raw_bits = self.generate_raw_bits(target_bits)
            clean_bits = self.von_neumann_extractor(raw_bits)
            unbiased_bits += clean_bits
            
        # Truncate to the exact length needed
        final_entropy_bits = unbiased_bits[:target_bits]
        
        # Convert bitstring to a byte array
        byte_array = bytearray()
        for i in range(0, len(final_entropy_bits), 8):
            byte_array.append(int(final_entropy_bits[i:i+8], 2))
            
        # For security tokens, it's best practice to pass the hardware entropy 
        # through a cryptographic hash function (like SHA-256) to guarantee 
        # an ideal uniform distribution and avalanche effect.
        hasher = hashlib.sha256()
        hasher.update(byte_array)
        token_bytes = hasher.digest()
        
        # Return the requested number of bytes in hex format
        return binascii.hexlify(token_bytes[:num_bytes]).decode('utf-8')


if __name__ == "__main__":
    print("--- Quantum Security Token Generator ---")
    
    # Set to True and provide your IBM API key to use real Quantum Hardware
    # You can get an API key at https://quantum.ibm.com/
    USE_IBM_HARDWARE = True
    IBM_API_KEY = os.getenv("IBM_QUANTUM_TOKEN")
    
    try:
        # Initialize the Quantum RNG
        qrng = QuantumRNG(use_real_hardware=USE_IBM_HARDWARE, ibm_token=IBM_API_KEY)
        
        # Generate a 256-bit (32 byte) secure token
        print("\nInitiating token generation process...")
        token = qrng.generate_security_token(num_bytes=32)
        
        print("\n✅ Success! Your Quantum-Generated Security Token:")
        print("-" * 64)
        print(token)
        print("-" * 64)
        
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

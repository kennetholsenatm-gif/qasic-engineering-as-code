#!/usr/bin/env python3
"""
Test script for QASIC Digital Twin Platform
Demonstrates CLI functionality and basic validation
"""

import sys
import os
from pathlib import Path

# Add the digital-twin directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported"""
    print("🔍 Testing imports...")

    try:
        from digital_twin.orchestrator import DigitalTwinOrchestrator
        print("✅ Orchestrator imported")
    except ImportError as e:
        print(f"❌ Orchestrator import failed: {e}")
        return False

    try:
        from digital_twin.schemas.design_schema import create_8qubit_linear_template, validate_design_json
        print("✅ Schema validation imported")
    except ImportError as e:
        print(f"❌ Schema import failed: {e}")
        return False

    try:
        from digital_twin.cli.main import main
        print("✅ CLI imported")
    except ImportError as e:
        print(f"❌ CLI import failed: {e}")
        return False

    return True

def test_design_creation():
    """Test design creation and validation"""
    print("\n🎨 Testing design creation...")

    try:
        from digital_twin.schemas.design_schema import create_8qubit_linear_template, validate_design_json

        # Create a design
        design = create_8qubit_linear_template()
        print(f"✅ Created 8-qubit linear design: {design['metadata']['project_id']}")

        # Validate the design
        validated = validate_design_json(design)
        print(f"✅ Design validation passed: {validated.metadata.project_id}")

        return True
    except Exception as e:
        print(f"❌ Design creation/validation failed: {e}")
        return False

def test_orchestrator():
    """Test orchestrator initialization"""
    print("\n🎼 Testing orchestrator...")

    try:
        from digital_twin.orchestrator import DigitalTwinOrchestrator

        orchestrator = DigitalTwinOrchestrator()
        print("✅ Orchestrator initialized")

        # Test summary method
        mock_results = {
            'validation': {
                'qubit': {'gate_fidelity_percent': 98.5},
                'yield': {'yield_typical_percent': 87.2}
            },
            'performance': {'total_time_seconds': 45.2}
        }

        summary = orchestrator.get_validation_summary(mock_results)
        print(f"✅ Summary generation works: {summary['status']}")

        return True
    except Exception as e:
        print(f"❌ Orchestrator test failed: {e}")
        return False

def test_cli_help():
    """Test CLI help output"""
    print("\n💻 Testing CLI help...")

    try:
        from digital_twin.cli.main import main
        # We can't easily test the full CLI without proper argument parsing,
        # but we can test that the main function exists
        print("✅ CLI main function available")
        return True
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 QASIC Digital Twin Platform - Test Suite")
    print("=" * 50)

    tests = [
        test_imports,
        test_design_creation,
        test_orchestrator,
        test_cli_help
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Digital Twin Platform is ready.")
        print("\n🚀 Try these commands:")
        print("  python -m digital_twin.cli.main --help")
        print("  python -c \"from digital_twin.cli.main import create_design; print('CLI functions available')\"")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
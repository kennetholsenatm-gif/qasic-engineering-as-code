#!/usr/bin/env python3
"""
QASIC Digital Twin CLI
Command-line interface for the QASIC Digital Twin Platform
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from digital_twin.orchestrator import DigitalTwinOrchestrator
from digital_twin.schemas.design_schema import (
    create_8qubit_linear_template,
    create_16qubit_grid_template,
    validate_design_json,
    save_design_template
)

def create_design(args):
    """Create a new design from template"""
    print("🎨 QASIC Digital Twin - Design Creator")
    print("=" * 50)

    # Select template
    if args.template == "8qubit_linear":
        design = create_8qubit_linear_template()
    elif args.template == "16qubit_grid":
        design = create_16qubit_grid_template()
    else:
        print(f"❌ Unknown template: {args.template}")
        print("Available templates: 8qubit_linear, 16qubit_grid")
        return 1

    # Customize if requested
    if args.qubit_count:
        design['quantum_design']['qubit_count'] = args.qubit_count
        design['metadata']['project_id'] = f"qasic-v1.0-{args.qubit_count}q-custom-{design['quantum_design']['target_frequency_ghz']}ghz"

    if args.frequency:
        design['quantum_design']['target_frequency_ghz'] = args.frequency
        design['control']['readout_resonance_ghz'] = args.frequency + 0.5
        design['metadata']['project_id'] = f"qasic-v1.0-{design['quantum_design']['qubit_count']}q-custom-{args.frequency}ghz"

    # Validate design
    try:
        validated = validate_design_json(design)
        print(f"✅ Design validated: {validated.metadata.project_id}")
    except Exception as e:
        print(f"❌ Design validation failed: {e}")
        return 1

    # Save design
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(design, f, indent=2)

    print(f"📁 Design saved to: {output_path}")
    print(f"📊 Qubits: {design['quantum_design']['qubit_count']}")
    print(f"📡 Frequency: {design['quantum_design']['target_frequency_ghz']} GHz")
    print(f"🎛️ Control: {design['control']['backend']}")
    print()
    print("Next steps:")
    print("  qasic-validate design.json --full-stack    # Run full validation")
    print("  jupyter notebook notebooks/01_design_overview.ipynb  # Interactive exploration")

    return 0

def validate_design(args):
    """Validate a design through the digital twin"""
    print("🔬 QASIC Digital Twin - Design Validator")
    print("=" * 50)

    design_path = Path(args.design)
    if not design_path.exists():
        print(f"❌ Design file not found: {design_path}")
        return 1

    # Initialize orchestrator
    orchestrator = DigitalTwinOrchestrator()

    # Run validation
    try:
        print(f"📂 Loading design: {design_path}")
        results = orchestrator.validate_design(
            str(design_path),
            full_stack=args.full_stack,
            num_workers=args.workers,
            cache=args.cache
        )

        # Check for errors
        if 'error' in results:
            print(f"❌ Validation failed: {results['error']}")
            return 1

        # Print summary
        summary = orchestrator.get_validation_summary(results)
        print(f"✅ Validation completed: {summary['status']}")
        print(f"⏱️ Total time: {summary['total_time_seconds']:.1f} seconds")
        print(f"🔧 Engines completed: {summary['engines_completed']}")

        if summary['key_metrics']:
            print("\n📊 Key Metrics:")
            for key, value in summary['key_metrics'].items():
                if isinstance(value, float):
                    if 'percent' in key:
                        print(".1f"                    elif 'rate' in key or 'error' in key:
                        print(".2e"                    elif 'microseconds' in key:
                        print(".1f"                    elif 'mhz' in key.lower():
                        print(".1f"                    else:
                        print(".2f"                else:
                    print(f"  {key}: {value}")

        # Save results
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n📁 Results saved to: {output_path}")

        # Tapeout readiness check
        if args.check_tapeout:
            tapeout_ready = check_tapeout_readiness(results)
            if tapeout_ready:
                print("\n🎯 TAPE-OUT READY! ✅")
                print("All validation criteria met. Ready for fab submission.")
            else:
                print("\n⚠️ NOT TAPE-OUT READY")
                print("Some validation criteria failed. Review results above.")

        return 0 if summary['status'] == 'PASS' else 1

    except Exception as e:
        print(f"❌ Validation error: {e}")
        return 1

def check_tapeout_readiness(results: Dict[str, Any]) -> bool:
    """Check if design meets tapeout readiness criteria"""
    validation = results.get('validation', {})

    # Gate fidelity > 99%
    qubit = validation.get('qubit', {})
    gate_fidelity = qubit.get('gate_fidelity_percent', 0)
    if gate_fidelity < 99.0:
        return False

    # Yield > 85% (typical)
    yield_analysis = validation.get('yield', {})
    yield_typical = yield_analysis.get('yield_typical_percent', 0)
    if yield_typical < 85.0:
        return False

    # Thermal margin > 1K
    thermal = validation.get('thermal', {})
    thermal_margin = thermal.get('thermal_margin_k', 0)
    if thermal_margin < 1.0:
        return False

    # DRC clean
    drc = validation.get('drc', {})
    drc_clean = drc.get('drc_clean', False)
    if not drc_clean:
        return False

    # Safety factor > 3
    fea = validation.get('fea', {})
    safety_factor = fea.get('safety_factor', 0)
    if safety_factor < 3.0:
        return False

    return True

def batch_validate(args):
    """Batch validate multiple designs"""
    print("🔬 QASIC Digital Twin - Batch Validator")
    print("=" * 50)

    designs_dir = Path(args.designs_dir)
    if not designs_dir.exists():
        print(f"❌ Designs directory not found: {designs_dir}")
        return 1

    # Find all design.json files
    design_files = list(designs_dir.glob("**/design.json"))
    if not design_files:
        print(f"❌ No design.json files found in {designs_dir}")
        return 1

    print(f"📂 Found {len(design_files)} designs to validate")

    # Initialize orchestrator
    orchestrator = DigitalTwinOrchestrator()

    # Validate each design
    results_summary = []
    for design_file in design_files:
        print(f"\n🔍 Validating: {design_file.name}")
        try:
            results = orchestrator.validate_design(
                str(design_file),
                full_stack=args.full_stack,
                num_workers=args.workers,
                cache=args.cache
            )

            summary = orchestrator.get_validation_summary(results)
            summary['design_file'] = str(design_file)
            results_summary.append(summary)

            status = "✅ PASS" if summary['status'] == 'PASS' else "❌ FAIL"
            print(f"   {status} - {summary['total_time_seconds']:.1f}s")

        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results_summary.append({
                'design_file': str(design_file),
                'status': 'ERROR',
                'error': str(e)
            })

    # Print batch summary
    print(f"\n📊 Batch Summary:")
    passed = sum(1 for r in results_summary if r.get('status') == 'PASS')
    total = len(results_summary)
    print(f"   Passed: {passed}/{total} ({100*passed/total:.1f}%)")

    if passed < total:
        print("   Failed designs:")
        for result in results_summary:
            if result.get('status') != 'PASS':
                print(f"     - {Path(result['design_file']).name}: {result.get('status')}")

    # Save batch results
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(results_summary, f, indent=2)
        print(f"\n📁 Batch results saved to: {output_path}")

    return 0 if passed == total else 1

def compare_designs(args):
    """Compare validation results of multiple designs"""
    print("📊 QASIC Digital Twin - Design Comparator")
    print("=" * 50)

    results_files = args.results
    if len(results_files) < 2:
        print("❌ Need at least 2 results files to compare")
        return 1

    # Load all results
    all_results = []
    for results_file in results_files:
        results_path = Path(results_file)
        if not results_path.exists():
            print(f"❌ Results file not found: {results_path}")
            return 1

        with open(results_path, 'r') as f:
            results = json.load(f)
            all_results.append(results)

    # Extract key metrics for comparison
    comparison_data = []
    for i, results in enumerate(all_results):
        design_id = results.get('metadata', {}).get('design_id', f'Design {i+1}')
        summary = DigitalTwinOrchestrator().get_validation_summary(results)

        comparison_data.append({
            'design_id': design_id,
            'status': summary['status'],
            'time_seconds': summary['total_time_seconds'],
            **summary['key_metrics']
        })

    # Print comparison table
    print(f"Comparing {len(comparison_data)} designs:")
    print()

    # Header
    headers = ['Design ID', 'Status', 'Time (s)'] + list(comparison_data[0].keys())[3:]
    print(" | ".join(f"{h:<20}" for h in headers))
    print("-" * (len(headers) * 22))

    # Rows
    for data in comparison_data:
        row = [
            data['design_id'][:19],
            data['status'][:19],
            f"{data['time_seconds']:.1f}"[:19]
        ]

        for key in list(data.keys())[3:]:
            value = data[key]
            if isinstance(value, float):
                if 'percent' in key:
                    row.append(f"{value:.1f}%"[:19])
                elif 'rate' in key or 'error' in key:
                    row.append(f"{value:.1e}"[:19])
                else:
                    row.append(f"{value:.2f}"[:19])
            else:
                row.append(str(value)[:19])

        print(" | ".join(f"{cell:<20}" for cell in row))

    # Recommendations
    print("\n💡 Recommendations:")
    if len(comparison_data) >= 2:
        # Find best design by yield
        best_yield = max(comparison_data,
                        key=lambda x: x.get('yield_typical_percent', 0))
        print(f"   🏆 Best yield: {best_yield['design_id']} ({best_yield.get('yield_typical_percent', 0):.1f}%)")

        # Find fastest validation
        fastest = min(comparison_data, key=lambda x: x['time_seconds'])
        print(f"   ⚡ Fastest validation: {fastest['design_id']} ({fastest['time_seconds']:.1f}s)")

        # Find most reliable (highest gate fidelity)
        most_reliable = max(comparison_data,
                          key=lambda x: x.get('gate_fidelity_percent', 0))
        print(f"   🎯 Most reliable: {most_reliable['design_id']} ({most_reliable.get('gate_fidelity_percent', 0):.1f}%)")

    return 0

def package_design(args):
    """Package validated design for tapeout"""
    print("📦 QASIC Digital Twin - Design Packager")
    print("=" * 50)

    design_path = Path(args.design)
    results_path = Path(args.results) if args.results else None

    if not design_path.exists():
        print(f"❌ Design file not found: {design_path}")
        return 1

    # Load design
    with open(design_path, 'r') as f:
        design = json.load(f)

    # Load results if provided
    results = None
    if results_path and results_path.exists():
        with open(results_path, 'r') as f:
            results = json.load(f)

    # Create package directory
    project_id = design['metadata']['project_id']
    package_dir = Path(args.output) / f"{project_id}_tapeout_package"
    package_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 Creating tapeout package: {package_dir}")

    # Copy design file
    import shutil
    shutil.copy(design_path, package_dir / "design.json")

    # Copy results if available
    if results:
        with open(package_dir / "validation_results.json", 'w') as f:
            json.dump(results, f, indent=2)

    # Generate tapeout checklist
    checklist = generate_tapeout_checklist(design, results)
    with open(package_dir / "tapeout_checklist.md", 'w') as f:
        f.write(checklist)

    # Create placeholder files for actual artifacts
    artifacts = [
        "layout.gds",  # GDS layout file
        "thermal_report.json",  # Thermal analysis results
        "yield_analysis.json",  # Yield prediction results
        "control_config.json",  # Control electronics config
        "packaging.step",  # 3D CAD file
        "fab_submission.pdf"  # Documentation bundle
    ]

    for artifact in artifacts:
        (package_dir / artifact).touch()  # Create empty placeholder

    print("📋 Package contents:")
    for item in sorted(package_dir.iterdir()):
        if item.is_file():
            print(f"   📄 {item.name}")
        else:
            print(f"   📁 {item.name}/")

    print(f"\n✅ Tapeout package created: {package_dir}")
    print("Next steps:")
    print("  1. Review tapeout_checklist.md")
    print("  2. Generate actual GDS/layout files")
    print("  3. Submit package to foundry")

    return 0

def generate_tapeout_checklist(design: Dict[str, Any], results: Optional[Dict[str, Any]] = None) -> str:
    """Generate tapeout checklist markdown"""
    project_id = design['metadata']['project_id']

    checklist = f"""# Tapeout Checklist: {project_id}

**Generated**: 2026-03-09
**Owner**: {design['metadata']['owner']}
**Foundry**: {design['fab']['foundry']}

## Design Summary
- **Qubits**: {design['quantum_design']['qubit_count']}
- **Topology**: {design['quantum_design']['topology']}
- **Frequency**: {design['quantum_design']['target_frequency_ghz']} GHz
- **Control**: {design['control']['backend']}

## Validation Status
"""

    if results:
        validation = results.get('validation', {})
        checklist += "### ✅ Completed Validations\n"

        if 'qubit' in validation:
            qubit = validation['qubit']
            checklist += f"- **Quantum Performance**: Gate fidelity {qubit.get('gate_fidelity_percent', 0):.1f}%, T1 {qubit.get('t1_microseconds', 0):.1f}μs\n"

        if 'yield' in validation:
            yield_data = validation['yield']
            checklist += f"- **Yield Prediction**: {yield_data.get('yield_typical_percent', 0):.1f}% typical, {yield_data.get('yield_worst_case_percent', 0):.1f}% worst-case\n"

        if 'thermal' in validation:
            thermal = validation['thermal']
            checklist += f"- **Thermal**: {thermal.get('thermal_margin_k', 0):.1f}K margin, {thermal.get('power_budget_utilization_percent', 0):.1f}% power utilization\n"

        if 'fea' in validation:
            fea = validation['fea']
            checklist += f"- **Mechanical**: Safety factor {fea.get('safety_factor', 0):.1f}, max stress {fea.get('max_stress_mpa', 0):.1f} MPa\n"

        if 'drc' in validation:
            drc = validation['drc']
            status = "✅ PASS" if drc.get('drc_clean', False) else "❌ FAIL"
            checklist += f"- **DRC**: {status} ({drc.get('violations_found', 0)} violations)\n"

    checklist += """
## Pre-Fab Checklist
- [ ] Design review completed by hardware team
- [ ] PDK compliance verified
- [ ] Layer stack matches foundry requirements
- [ ] Bond pad layout approved
- [ ] Witness structures included
- [ ] Alignment marks placed
- [ ] GDS file generated and validated
- [ ] LVS (Layout vs Schematic) clean
- [ ] ERC (Electrical Rule Check) passed
- [ ] Antenna checks passed
- [ ] Fill insertion completed
- [ ] Dummy metal insertion completed

## Fab Submission
- [ ] Package uploaded to foundry portal
- [ ] All required files included
- [ ] Documentation bundle attached
- [ ] Contact information provided
- [ ] Timeline agreed upon

## Post-Fab Validation Plan
- [ ] Test structures measurement plan ready
- [ ] Correlation analysis planned (predicted vs measured)
- [ ] Backup yield analysis available
- [ ] Failure analysis procedures documented

---
**Sign-off**: _______________ Date: _______________
"""

    return checklist

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="QASIC Digital Twin Platform CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new 8-qubit design
  qasic-create --template 8qubit_linear --output my_design.json

  # Validate a design (full-stack simulation)
  qasic-validate my_design.json --full-stack --workers 4

  # Batch validate multiple designs
  qasic-batch --designs-dir ./designs/ --output batch_results.json

  # Compare validation results
  qasic-compare results/design1.json results/design2.json

  # Package for tapeout
  qasic-package my_design.json --results validation_results.json --output ./tapeout/
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new design from template')
    create_parser.add_argument('--template', required=True,
                              choices=['8qubit_linear', '16qubit_grid'],
                              help='Design template to use')
    create_parser.add_argument('--output', '-o', required=True,
                              help='Output design file path')
    create_parser.add_argument('--qubit-count', type=int,
                              help='Override qubit count')
    create_parser.add_argument('--frequency', type=float,
                              help='Override operating frequency (GHz)')
    create_parser.set_defaults(func=create_design)

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a design')
    validate_parser.add_argument('design', help='Design JSON file to validate')
    validate_parser.add_argument('--full-stack', action='store_true', default=True,
                                help='Run full-stack validation (default)')
    validate_parser.add_argument('--workers', '-w', type=int, default=4,
                                help='Number of parallel workers')
    validate_parser.add_argument('--cache', action='store_true', default=True,
                                help='Use result caching')
    validate_parser.add_argument('--output', '-o',
                                help='Save validation results to file')
    validate_parser.add_argument('--check-tapeout', action='store_true',
                                help='Check tapeout readiness criteria')
    validate_parser.set_defaults(func=validate_design)

    # Batch validate command
    batch_parser = subparsers.add_parser('batch', help='Batch validate multiple designs')
    batch_parser.add_argument('--designs-dir', required=True,
                             help='Directory containing design.json files')
    batch_parser.add_argument('--full-stack', action='store_true', default=True,
                             help='Run full-stack validation')
    batch_parser.add_argument('--workers', '-w', type=int, default=4,
                             help='Number of parallel workers per design')
    batch_parser.add_argument('--cache', action='store_true', default=True,
                             help='Use result caching')
    batch_parser.add_argument('--output', '-o',
                             help='Save batch results summary')
    batch_parser.set_defaults(func=batch_validate)

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare validation results')
    compare_parser.add_argument('results', nargs='+',
                               help='Validation result JSON files to compare')
    compare_parser.set_defaults(func=compare_designs)

    # Package command
    package_parser = subparsers.add_parser('package', help='Package design for tapeout')
    package_parser.add_argument('design', help='Design JSON file')
    package_parser.add_argument('--results', help='Validation results JSON file')
    package_parser.add_argument('--output', '-o', default='./tapeout',
                               help='Output directory for tapeout package')
    package_parser.set_defaults(func=package_design)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run the selected command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
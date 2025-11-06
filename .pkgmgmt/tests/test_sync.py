#!/usr/bin/env python3
"""
Test that generated files are in sync with packages.yaml.

This ensures developers regenerate files after editing packages.yaml.
"""

import sys
import subprocess
import tempfile
import shutil
from pathlib import Path


def test_generated_files_in_sync():
    """
    Test that generated files match what would be generated from packages.yaml.

    This prevents commits where packages.yaml was edited but generated files
    weren't regenerated.
    """
    script_dir = Path(__file__).parent.parent
    repo_root = script_dir.parent

    # Files that should be generated
    expected_files = [
        repo_root / 'dot_config/Brewfile_darwin',
        repo_root / 'dot_config/packages-apt.txt.tmpl',
        repo_root / 'dot_config/packages-msys2.txt.tmpl',
        repo_root / 'dot_config/packages-pacman.txt.tmpl',
        repo_root / 'dot_config/packages-dnf.txt.tmpl',
        repo_root / 'dot_config/packages-raspi.txt.tmpl',
    ]

    # Check all expected files exist
    missing_files = [f for f in expected_files if not f.exists()]
    if missing_files:
        print("❌ Missing generated files:")
        for f in missing_files:
            print(f"   - {f}")
        print("\nRun: .pkgmgmt/generate_packages.py")
        return False

    # Create temp directory to generate fresh copies
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Copy packages.yaml to temp
        shutil.copy(script_dir / 'packages.yaml', tmpdir / 'packages.yaml')

        # Create a modified generator that outputs to temp dir
        # For simplicity, we'll just run the generator and compare outputs

        # Read current file contents
        current_files = {}
        for f in expected_files:
            with open(f, 'r') as file:
                current_files[f.name] = file.read()

        # Run generator
        result = subprocess.run(
            [sys.executable, str(script_dir / 'generate_packages.py')],
            cwd=repo_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("❌ Generator failed:")
            print(result.stderr)
            return False

        # Read newly generated files
        new_files = {}
        for f in expected_files:
            with open(f, 'r') as file:
                new_files[f.name] = file.read()

        # Compare
        mismatched = []
        for name in current_files:
            if current_files[name] != new_files[name]:
                mismatched.append(name)

        if mismatched:
            print("❌ Generated files are out of sync with packages.yaml:")
            for name in mismatched:
                print(f"   - {name}")
            print("\nFiles were modified by running generate_packages.py")
            print("This means the committed files don't match packages.yaml")
            print("\nTo fix:")
            print("1. Run: .pkgmgmt/generate_packages.py")
            print("2. Commit the updated files")

            # Show what changed
            for name in mismatched:
                current_lines = current_files[name].split('\n')
                new_lines = new_files[name].split('\n')

                # Simple diff
                if len(current_lines) != len(new_lines):
                    print(f"\n{name}: Line count changed ({len(current_lines)} -> {len(new_lines)})")
                else:
                    for i, (old, new) in enumerate(zip(current_lines, new_lines)):
                        if old != new:
                            print(f"\n{name} line {i+1}:")
                            print(f"  Was: {old}")
                            print(f"  Now: {new}")
                            break

            return False

    print("✓ All generated files are in sync with packages.yaml")
    return True


if __name__ == '__main__':
    success = test_generated_files_in_sync()
    sys.exit(0 if success else 1)

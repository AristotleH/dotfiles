#!/usr/bin/env python3
"""
Test that generate_shell.py produces the expected files in a temp directory.

Validates that the generator creates all expected files for all 4 shells
with the correct header and content, without touching the chezmoi source tree.
"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path so we can import the generator
sys.path.insert(0, str(Path(__file__).parent.parent))
from generate_shell import (
    HEADER,
    SHELLS,
    SHELL_FUNC_EXT,
    SHELL_MODULE_EXT,
    generate_all,
    generate_function,
    generate_module,
    get_output_dirs,
    load_manifest,
    validate_manifest,
)


def test_generate_to_tempdir():
    """
    Generate shell files to a temp dir and verify:
    - All expected files for all 4 shells are created
    - All start with HEADER
    - Content matches generate_function/generate_module output
    """
    script_dir = Path(__file__).parent.parent
    manifest_path = script_dir / "shell.yaml"

    try:
        import yaml
    except ImportError:
        print("SKIP: pyyaml not installed")
        return True

    if not manifest_path.exists():
        print(f"shell.yaml not found at {manifest_path}")
        return False

    manifest = load_manifest(manifest_path)
    errors = validate_manifest(manifest)
    if errors:
        print("Validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        repo_root = script_dir.parent
        generated = generate_all(manifest, target, repo_root)
        dirs = get_output_dirs(target, repo_root)

        # Build expected file list
        expected_files = []
        for func in manifest.get("functions", []):
            name = func["name"]
            for shell in SHELLS:
                func_ext = SHELL_FUNC_EXT[shell]
                func_dir = dirs[shell]["functions"]
                expected_files.append(func_dir / f"{name}{func_ext}")

        for mod in manifest.get("modules", []):
            name = mod["name"]
            prefix = mod["prefix"]
            for shell in SHELLS:
                mod_ext = SHELL_MODULE_EXT[shell]
                mod_dir = dirs[shell]["modules"]
                expected_files.append(mod_dir / f"{prefix}-{name}{mod_ext}")

        # Check all expected files were created
        missing = [f for f in expected_files if not f.exists()]
        if missing:
            print("Missing generated files:")
            for f in missing:
                print(f"  - {f}")
            return False

        # Check count matches
        if len(generated) != len(expected_files):
            print(f"Expected {len(expected_files)} files, got {len(generated)}")
            return False

        # Check all files start with HEADER
        bad_header = []
        for f in expected_files:
            content = f.read_text()
            if not content.startswith(HEADER):
                bad_header.append(f.name)
        if bad_header:
            print("Files missing HEADER:")
            for name in bad_header:
                print(f"  - {name}")
            return False

        # Verify content matches generator output
        for func in manifest.get("functions", []):
            name = func["name"]
            for shell in SHELLS:
                func_ext = SHELL_FUNC_EXT[shell]
                func_dir = dirs[shell]["functions"]
                path = func_dir / f"{name}{func_ext}"
                expected = generate_function(func, shell)
                actual = path.read_text()
                if actual != expected:
                    print(f"Content mismatch: {path.name} ({shell})")
                    print(f"  Expected:\n{expected[:200]}")
                    print(f"  Actual:\n{actual[:200]}")
                    return False

        for mod in manifest.get("modules", []):
            name = mod["name"]
            prefix = mod["prefix"]
            for shell in SHELLS:
                mod_ext = SHELL_MODULE_EXT[shell]
                mod_dir = dirs[shell]["modules"]
                path = mod_dir / f"{prefix}-{name}{mod_ext}"
                expected = generate_module(mod, shell)
                actual = path.read_text()
                if actual != expected:
                    print(f"Content mismatch: {path.name} ({shell})")
                    print(f"  Expected:\n{expected[:200]}")
                    print(f"  Actual:\n{actual[:200]}")
                    return False

    print(f"All {len(expected_files)} generated shell files verified in temp dir "
          f"({len(SHELLS)} shells)")
    return True


if __name__ == "__main__":
    success = test_generate_to_tempdir()
    sys.exit(0 if success else 1)

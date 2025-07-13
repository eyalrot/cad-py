#!/usr/bin/env python3
"""Script to generate Python gRPC code from protobuf definitions."""

import os
import subprocess
import sys
from pathlib import Path


def generate_grpc_code():
    """Generate Python gRPC code from proto files."""
    # Get the proto directory
    proto_dir = Path(__file__).parent
    backend_dir = proto_dir.parent.parent
    output_dir = proto_dir / "generated"

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Create __init__.py file
    (output_dir / "__init__.py").touch()

    # Find all .proto files
    proto_files = list(proto_dir.glob("*.proto"))

    if not proto_files:
        print("No .proto files found!")
        return False

    print(f"Found {len(proto_files)} proto files:")
    for proto_file in proto_files:
        print(f"  - {proto_file.name}")

    # Generate Python code for each proto file
    for proto_file in proto_files:
        print(f"\nGenerating code for {proto_file.name}...")

        cmd = [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"--proto_path={proto_dir}",
            f"--python_out={output_dir}",
            f"--grpc_python_out={output_dir}",
            str(proto_file),
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"  ✓ Generated code for {proto_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to generate code for {proto_file.name}")
            print(f"    Error: {e.stderr}")
            return False
        except FileNotFoundError:
            print(
                "  ✗ grpc_tools.protoc not found. Install with: pip install grpcio-tools"
            )
            return False

    print(f"\nGenerated files in {output_dir}:")
    for generated_file in sorted(output_dir.glob("*.py")):
        print(f"  - {generated_file.name}")

    # Fix imports in generated files
    fix_imports(output_dir)

    return True


def fix_imports(output_dir: Path):
    """Fix relative imports in generated gRPC files."""
    print("\nFixing imports in generated files...")

    for py_file in output_dir.glob("*_pb2_grpc.py"):
        print(f"  Fixing imports in {py_file.name}")

        # Read the file
        content = py_file.read_text()

        # Fix imports - replace absolute imports with relative
        imports_to_fix = [
            "import geometry_pb2",
            "import layer_pb2",
            "import entity_pb2",
            "import document_pb2",
        ]

        for import_line in imports_to_fix:
            if import_line in content:
                new_import = import_line.replace("import ", "from . import ")
                content = content.replace(import_line, new_import)

        # Write back the fixed content
        py_file.write_text(content)


if __name__ == "__main__":
    print("Generating gRPC Python code...")
    success = generate_grpc_code()

    if success:
        print("\n✓ gRPC code generation completed successfully!")
    else:
        print("\n✗ gRPC code generation failed!")
        sys.exit(1)

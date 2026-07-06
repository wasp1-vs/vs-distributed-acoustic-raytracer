import json
import subprocess
from pathlib import Path


def run_rust_and_load_json(
    rust_binary_path: str,
    json_path: str
) -> dict:
    rust_binary = Path(rust_binary_path).resolve()
    json_file = Path(json_path)

    if not rust_binary.exists():
        raise FileNotFoundError(f"Rust binary not found: {rust_binary}")

    if not rust_binary.is_file():
        raise FileNotFoundError(f"Path is not a file: {rust_binary}")

    if json_file.name != "ir_output.json":
        raise ValueError(
            "Rust currently writes to 'ir_output.json' only. "
            f"Got: {json_file.name}"
        )

    # Walk up from the binary to find the directory containing input_config.json
    rust_service_dir = rust_binary.parent
    for parent in rust_binary.parents:
        if (parent / "input_config.json").exists():
            rust_service_dir = parent
            break

    output_file = rust_service_dir / "ir_output.json"

    # Remove stale output so we never accidentally load results from a previous run
    if output_file.exists():
        output_file.unlink()

    result = subprocess.run(
        [str(rust_binary)],
        cwd=rust_service_dir,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Rust binary failed (code {result.returncode}).\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )

    if not output_file.exists():
        raise FileNotFoundError(
            f"Rust finished but ir_output.json was not created: {output_file}"
        )

    try:
        with output_file.open("r", encoding="utf-8") as file:
            ir_data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(f"ir_output.json is not valid JSON: {output_file}") from error

    return ir_data
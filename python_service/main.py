import json
import sys
from pathlib import Path

# Import all the modules your team built
from rust_runner import run_rust_and_load_json
from wav_handler import read_wav, write_wav
from convolution import convolve
from obj_parser import export_room_geometry


def main():
    print("--- Starting Acoustic Reverb Pipeline ---")

    base_dir = Path(__file__).resolve().parent


    binary_name = "rust_service.exe" if sys.platform == "win32" else "rust_service"
    rust_binary_path = str(base_dir / ".." / "rust_service" / "target" / "release" / binary_name)
    json_path = "ir_output.json"

    input_wav_path = str(base_dir / "test_dry_audio.wav")
    output_wav_path = str(base_dir / "final_reverb_audio.wav")

    # Quick check to make sure the user provided a test audio file
    if not Path(input_wav_path).exists():
        print(f"ERROR: Could not find '{input_wav_path}'.")
        print("Please place a dry audio file in the folder to process.")
        sys.exit(1)

    # ---------------------------------------------------------
    # STEP 0: OBJ -> room_geometry.json
    # ---------------------------------------------------------
    # Find rust_service directory (contains input_config.json)
    rust_service_dir = Path(rust_binary_path).resolve().parent
    for parent in Path(rust_binary_path).resolve().parents:
        if (parent / "input_config.json").exists():
            rust_service_dir = parent
            break
    try:
        rust_config = json.loads((rust_service_dir / "input_config.json").read_text())
        wall_material = rust_config.get("wall_material", "concrete")
    except Exception:
        wall_material = "concrete"
    room_geometry_path = rust_service_dir / "room_geometry.json"
    room_obj_path = base_dir / "room.obj"
    if room_obj_path.exists():
        print(f"\n[0/4] Found room.obj – generating room_geometry.json (material: {wall_material}) ...")
        try:
            export_room_geometry(str(room_obj_path), wall_material, str(room_geometry_path))
        except Exception as e:
            print(f"WARNING: Could not export room geometry: {e}")
    else:
        print("\n[0/4] No room.obj found – Rust uses built-in box geometry.")
        if room_geometry_path.exists():
            room_geometry_path.unlink()

    # ---------------------------------------------------------
    # STEP 1: RUN THE PHYSICS ENGINE (Rust)
    # ---------------------------------------------------------
    print("\n[1/4] Booting Rust Physics Engine...")
    try:
        ir_data = run_rust_and_load_json(rust_binary_path, json_path)
        hits_count = len(ir_data['hits']['delays_seconds'])
        print(f"SUCCESS: Engine finished. Received {hits_count} ray hits.")
    except Exception as e:
        print(f"FATAL ERROR during Rust execution:\n{e}")
        sys.exit(1)

    # ---------------------------------------------------------
    # STEP 2: LOAD THE AUDIO
    # ---------------------------------------------------------
    print(f"\n[2/4] Reading dry audio from: {input_wav_path}")
    dry_audio, sample_rate = read_wav(input_wav_path)

    # Ensure the audio matches the Rust engine's sample rate (usually 44100)
    rust_sample_rate = ir_data['metadata']['sample_rate']
    if sample_rate != rust_sample_rate:
        print(f"WARNING: Audio sample rate ({sample_rate}Hz) does not match Rust engine ({rust_sample_rate}Hz).")
        print("This might pitch-shift or distort the reverb!")

    # ---------------------------------------------------------
    # STEP 3: CONVOLUTION (The DSP Math)
    # ---------------------------------------------------------
    print("\n[3/4] Processing convolution (applying room acoustics)...")
    conv_material = ir_data.get("metadata", {}).get("wall_material")
    wet_audio = convolve(dry_audio, sample_rate, ir_data, material=conv_material)
    if conv_material:
        print(f"SUCCESS: Convolution finished with material '{conv_material}' (frequency-dependent absorption).")
    else:
        print("SUCCESS: Convolution finished (broadband).")

    # ---------------------------------------------------------
    # STEP 4: EXPORT THE FINAL AUDIO
    # ---------------------------------------------------------
    print(f"\n[4/4] Normalizing and exporting to: {output_wav_path}")
    write_wav(output_wav_path, wet_audio, sample_rate)

    print("\n--- Pipeline Complete! Go listen to your audio! ---")


if __name__ == "__main__":
    main()

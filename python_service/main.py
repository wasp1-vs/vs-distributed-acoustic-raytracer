import sys
from pathlib import Path

# Import all the modules your team built
from rust_runner import run_rust_and_load_json
from wav_handler import read_wav, write_wav
from convolution import convolve


def main():
    print("--- Starting Acoustic Reverb Pipeline ---")

    # 1. Define the input/output paths
    # (Adjust these paths depending on where your test audio is located)
    # Betriebssystem prüfen und .exe nur unter Windows anhängen
    binary_name = "rust_service.exe" if sys.platform == "win32" else "rust_service"
    rust_binary_path = f"../rust_service/target/release/{binary_name}" 
    json_path = "ir_output.json"

    input_wav_path = "test_dry_audio.wav"  # You need a dry audio file here!
    output_wav_path = "final_reverb_audio.wav"

    # Quick check to make sure the user provided a test audio file
    if not Path(input_wav_path).exists():
        print(f"ERROR: Could not find '{input_wav_path}'.")
        print("Please place a dry audio file in the folder to process.")
        sys.exit(1)

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
    wet_audio = convolve(dry_audio, sample_rate, ir_data)
    print("SUCCESS: Convolution finished.")

    # ---------------------------------------------------------
    # STEP 4: EXPORT THE FINAL AUDIO
    # ---------------------------------------------------------
    print(f"\n[4/4] Normalizing and exporting to: {output_wav_path}")
    write_wav(output_wav_path, wet_audio, sample_rate)

    print("\n--- Pipeline Complete! Go listen to your audio! ---")


if __name__ == "__main__":
    main()
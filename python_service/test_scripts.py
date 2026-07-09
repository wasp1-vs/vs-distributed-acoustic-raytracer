import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path
from convolution import convolve


def plot_rt60_decay(json_path):
    print("Loading ray hits...")
    with open(json_path, 'r') as f:
        data = json.load(f)

    delays = np.array(data['hits']['delays_seconds'])
    pressures = np.array(data['hits']['pressures'])

    # 1. Filter out absolute zero to prevent log(0) crashes
    valid_hits = pressures > 0
    delays = delays[valid_hits]
    pressures = pressures[valid_hits]

    # 2. Convert raw linear pressure to Logarithmic Decibels (dB)
    db_levels = 20 * np.log10(pressures)
    max_db = np.max(db_levels)
    db_levels = db_levels - max_db

    print(f"Plotting {len(delays)} valid ray hits...")

    # 3. Create the Plot
    plt.figure(figsize=(10, 6))

    # Plot the actual engine physics data
    plt.scatter(delays, db_levels, alpha=0.2, s=2, color='blue', label='Engine Ray Hits')

    # Plot the Mathematical Truth (Sabine Equation)
    # Target: 0 dB at 0 seconds -> -60 dB at 1.34 seconds
    plt.plot([0, 1.34], [0, -60], color='red', linewidth=3, linestyle='--', label='Sabine Prediction (1.34s)')

    # Formatting
    plt.title('Acoustic Energy Decay (RT60 Verification)')
    plt.xlabel('Time (Seconds)')
    plt.ylabel('Volume (Decibels)')
    plt.ylim(-80, 5)

    # Set X-axis limit to just past our expected RT60 time
    plt.xlim(0, max(delays.max(), 1.5))
    plt.grid(True, alpha=0.5)
    plt.legend()

    plt.show()
def test_dirac_convolution():
    sample_rate = 44100

    # 1. Create a Fake IR (exactly 2 hits)
    test_ir_data = {
        "metadata": {"sample_rate": sample_rate},
        "hits": {
            "delays_seconds": [0.5, 1.0],  # Hit at 0.5s and 1.0s
            "pressures": [0.8, 0.4]  # Energy levels
        }
    }

    # 2. Create a perfect Dirac Impulse (One sample of 1.0, the rest 0.0)
    dry_audio = np.zeros(sample_rate * 2)
    dry_audio[0] = 1.0

    # 3. Run the convolution
    wet_audio = convolve(dry_audio, sample_rate, test_ir_data)

    # 4. Prove the math: Check the exact samples
    sample_1 = int(0.5 * sample_rate)
    sample_2 = int(1.0 * sample_rate)

    print(f"Sample at 0.5s: Expected 0.8, Got {wet_audio[sample_1]:.4f}")
    print(f"Sample at 1.0s: Expected 0.4, Got {wet_audio[sample_2]:.4f}")


if __name__ == "__main__":
    #test_dirac_convolution()
    script_dir = Path(__file__).parent
    target_file = script_dir.parent / "rust_service" / "ir_output.json"
    plot_rt60_decay(target_file)
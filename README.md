# Acoustic Ray Tracer

## Overview
This project implements a high-performance acoustic ray tracing system to simulate realistic sound propagation and room acoustics. 

By decoupling the physics simulation from the audio processing, the system utilizes massive multithreading in Rust to compute millions of sound paths, generating highly accurate Impulse Responses (IR). These responses are then processed by a Python-based Digital Signal Processing (DSP) pipeline to apply physically accurate reverberation to audio files.

---

## Architecture

### 1. Physics Engine (Rust)
- **Core Simulation:** Simulates millions of sound rays using Monte Carlo integration.
- **Multithreading:** Utilizes **Rayon** for lock-free, data-parallel execution across all available CPU cores, replacing the need for external cluster distribution frameworks.
- **Acoustic Math:** Handles physical reflections, material absorption coefficients, geometric spreading (Inverse Square Law), and temporal smearing.
- **Data Export:** Serializes ray hit data (delays in seconds and pressure levels) into a clean JSON format (`ir_output.json`).

### 2. Orchestration & DSP Engine (Python)
- **Pipeline Management:** Orchestrates the Rust binary execution and manages memory ingestion.
- **Signal Processing:** Uses **NumPy** and **SciPy** for lightning-fast Fast Fourier Transform (FFT) convolution (`scipy.signal.oaconvolve`).
- **Audio Rendering:** Translates the raw physical delay data into a sample-accurate Impulse Response array, convolves it with dry `.wav` audio, normalizes the signal to prevent clipping, and exports the final "wet" reverberated audio.

### 3. Debugging & Visualization
- **Ray Path Plotting:** A dedicated **Matplotlib** visualizer parses `debug_paths.json` to draw room boundaries, speaker/mic constraints, and geometric ray bounces for visual verification of the physics math.

---

## Goals
- Physically accurate simulation of Early Reflections, Late Reverberation, and phase interference.
- Maximal CPU utilization via highly optimized local multithreading.
- Strict architectural decoupling of geometric simulation (Rust) from audio processing (Python).
- **Phase 1:** 2D Acoustic Simulation (Completed).
- **Phase 2:** Full 3D Volumetric Geometry Simulation (Planned).

---

## Tech Stack
- **Rust:** `rayon` (multithreading), `glam` (vector math), `serde` (JSON serialization).
- **Python:** Orchestration and DSP.
- **Python Libraries:** `numpy` (array mathematics), `scipy` (FFT convolution), `soundfile` (WAV I/O), `matplotlib` (visual debugging).

---

## Project Structure
```text
.
├── python_service/
│   ├── main.py             # Master orchestrator for the entire pipeline
│   ├── rust_runner.py      # Python-to-Rust subprocess interface
│   ├── test_rust_runner_manual.py      # Tests Rust binary JSON output.
│   ├── convolution.py      # DSP core (builds IR and convolves audio)
│   ├── test_dry_audio.wav      # Input audio source
│   ├── wav_handler.py      # Audio file read/write and normalization
│   └── visualizer.py       # Matplotlib graphical debugging tool
└── rust_service/           # Rust physics engine workspace
    ├── Cargo.toml
    ├── input_config.json   # Engine parameters (bounces, mic radius, rays)
    └── src/
        ├── main.rs         # Engine setup, materials, and wall configuration
        ├── simulation.rs   # Ray tracing loop and Rayon parallelization
        ├── geometry.rs     # Intersection math and epsilons
        └── export.rs       # JSON serialization structures

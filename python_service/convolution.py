"""DSP convolution core — Ticket 2 (Cem).

Applies a room impulse response (IR) produced by the Rust ray tracer to a
dry audio signal, yielding a wet (reverberated) signal.

Pipeline position:
    [Jian] subprocess + JSON ingestion  ->  ir_data (dict)
    [Kais] read_wav                     ->  (dry_audio, sample_rate)
    [Cem]  convolve(dry_audio, sample_rate, ir_data)  ->  wet_audio (raw)
    [Kais] write_wav                    ->  normalisiert + exportiert
    [Mier] main.py orchestriert
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy import signal

# Material-Datenbank (Per-Band-Absorption) kommt aus dem Rust-Service,
# damit Tracer und Faltung dieselben Koeffizienten nutzen.
_MATERIALS_JSON = Path(__file__).resolve().parent.parent / "rust_service" / "materials.json"


def build_impulse_response(
    delays_seconds: np.ndarray | list[float],
    pressures: np.ndarray | list[float],
    sample_rate: int,
) -> np.ndarray:
    """Diskretisiert eine Liste von Ray-Hits zu einem IR-Array.

    Jeder (delay, pressure) ist ein Schall-Strahl, der nach `delay` Sekunden
    mit Restdruck `pressure` am Mikrofon ankommt. Strahlen, die im gleichen
    Audio-Sample landen, werden akkumuliert.
    """
    delays = np.asarray(delays_seconds, dtype=np.float64)
    pressures = np.asarray(pressures, dtype=np.float64)

    if delays.shape != pressures.shape:
        raise ValueError(
            f"delays/pressures shape mismatch: {delays.shape} vs {pressures.shape}"
        )
    if delays.ndim != 1:
        raise ValueError(f"delays/pressures must be 1D, got ndim={delays.ndim}")
    if delays.size == 0:
        raise ValueError("no ray hits - cannot build impulse response")
    if (delays < 0).any():
        raise ValueError("negative delay in input")
    if sample_rate <= 0:
        raise ValueError(f"sample_rate must be positive, got {sample_rate}")

    indices = np.round(delays * sample_rate).astype(np.int64)
    ir_length = int(indices.max()) + 1
    ir = np.zeros(ir_length, dtype=np.float64)
    np.add.at(ir, indices, pressures)
    return ir


@lru_cache(maxsize=1)
def _load_materials(path: str) -> tuple[tuple[float, ...], dict[str, tuple[float, ...]]]:
    """Laedt center_freqs + Per-Band-Absorption aus materials.json (Rust-Service)."""
    data = json.loads(Path(path).read_text())
    centers = tuple(float(f) for f in data["center_freqs"])
    materials = {
        name: tuple(float(a) for a in m["absorption"])
        for name, m in data["materials"].items()
    }
    for name, alphas in materials.items():
        if len(alphas) != len(centers):
            raise ValueError(
                f"material '{name}': {len(alphas)} bands but {len(centers)} center_freqs"
            )
    return centers, materials


def available_materials() -> list[str]:
    _, materials = _load_materials(str(_MATERIALS_JSON))
    return sorted(materials)


def _octave_band_edges(centers: tuple[float, ...]) -> list[tuple[float | None, float | None]]:
    """(low, high) Grenzfrequenz pro Band; None = offenes Ende (Tief-/Hochpass)."""
    n = len(centers)
    edges: list[tuple[float | None, float | None]] = []
    for i in range(n):
        low = None if i == 0 else (centers[i - 1] * centers[i]) ** 0.5
        high = None if i == n - 1 else (centers[i] * centers[i + 1]) ** 0.5
        edges.append((low, high))
    return edges


def _bandpass(x: np.ndarray, low: float | None, high: float | None, nyquist: float) -> np.ndarray:
    if low is None:
        sos = signal.butter(4, high / nyquist, btype="lowpass", output="sos")
    elif high is None:
        sos = signal.butter(4, low / nyquist, btype="highpass", output="sos")
    else:
        sos = signal.butter(4, [low / nyquist, high / nyquist], btype="bandpass", output="sos")
    return signal.sosfiltfilt(sos, x)


def apply_material_absorption(
    ir: np.ndarray,
    sample_rate: int,
    material: str,
    mean_free_path_s: float = 0.02,
) -> np.ndarray:
    """Frequenzabhaengige Material-Daempfung auf eine Impulsantwort anwenden.

    Der Ray-Tracer liefert nur einen Skalar-Druck pro Hit; welche Frequenzen ein
    Material schluckt, geht dort verloren. Dieses Modell holt das im Frequenzraum
    zurueck: Ein Reflexions-Tap zur Zeit t hat ~ t / mean_free_path_s Reflexionen
    hinter sich. Pro Oktavband b mit Absorptionskoeffizient alpha_b bleibt nach
    n Reflexionen der Anteil (1 - alpha_b)^n. Hohe Baender mit hohem alpha
    (z.B. Teppich) klingen schneller aus als tiefe -> dunklerer, kuerzerer Hall;
    Beton (kleines alpha ueberall) bleibt hell und lang.

    Per-Surface-Materialtrennung (Teppich-Tap vs Beton-Tap) braucht
    Per-Band-Druecke aus dem Rust-Tracer - das ist hier bewusst nicht moeglich.
    """
    centers, materials = _load_materials(str(_MATERIALS_JSON))
    if material not in materials:
        raise ValueError(f"unknown material '{material}', known: {sorted(materials)}")
    if mean_free_path_s <= 0:
        raise ValueError(f"mean_free_path_s must be positive, got {mean_free_path_s}")
    if sample_rate <= 0:
        raise ValueError(f"sample_rate must be positive, got {sample_rate}")

    ir = np.asarray(ir, dtype=np.float64)
    nyquist = sample_rate / 2.0
    reflections = (np.arange(ir.size, dtype=np.float64) / sample_rate) / mean_free_path_s

    # sosfiltfilt braucht eine Mindestlaenge; zu kurze IRs nicht filtern.
    if ir.size <= 24:
        return ir

    shaped = np.zeros_like(ir)
    for (low, high), alpha in zip(_octave_band_edges(centers), materials[material]):
        band = _bandpass(ir, low, high, nyquist)
        gain = np.power(max(1e-6, 1.0 - alpha), reflections)
        shaped += band * gain
    return shaped


def convolve(
    dry_audio: np.ndarray,
    sample_rate: int,
    ir_data: dict,
    material: str | None = None,
    mean_free_path_s: float = 0.02,
) -> np.ndarray:
    if not isinstance(dry_audio, np.ndarray):
        raise TypeError(f"dry_audio must be np.ndarray, got {type(dry_audio).__name__}")
    if dry_audio.size == 0:
        raise ValueError("dry_audio is empty")

    try:
        meta = ir_data["metadata"]
        hits = ir_data["hits"]
        ir_sample_rate = int(meta["sample_rate"])
        delays = hits["delays_seconds"]
        pressures = hits["pressures"]
    except (KeyError, TypeError) as e:
        raise ValueError(f"ir_data has invalid schema: {e}") from e

    if ir_sample_rate != sample_rate:
        raise ValueError(
            f"sample rate mismatch - audio: {sample_rate} Hz, IR: {ir_sample_rate} Hz"
        )

    ir = build_impulse_response(delays, pressures, sample_rate)

    if material is not None:
        ir = apply_material_absorption(ir, sample_rate, material, mean_free_path_s)

    if dry_audio.ndim == 1:
        wet = signal.oaconvolve(dry_audio, ir, mode="full")
    elif dry_audio.ndim == 2:
        channels = [
            signal.oaconvolve(dry_audio[:, c], ir, mode="full")
            for c in range(dry_audio.shape[1])
        ]
        wet = np.stack(channels, axis=1)
    else:
        raise ValueError(f"dry_audio must be 1D or 2D, got ndim={dry_audio.ndim}")

    return wet.astype(np.float32)


if __name__ == "__main__":
    sample_rate = 44100
    ir_data = {
        "metadata": {
            "sample_rate": sample_rate,
            "rays_cast": 1_000_000,
            "rays_received": 3,
            "room_name": "SanityCheck",
        },
        "hits": {
            "delays_seconds": [0.0, 0.05, 0.12],
            "pressures": [1.0, 0.6, 0.3],
        },
    }
    duration_s = 1.0
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    dry = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    wet = convolve(dry, sample_rate, ir_data)

    print(f"dry length: {dry.size}")
    print(f"wet length: {wet.size}")
    print(f"wet peak:   {np.max(np.abs(wet)):.4f} (unnormalisiert)")
    print(f"wet dtype:  {wet.dtype}")
    print("sanity check ok.")

    
    rng = np.random.default_rng(0)
    n_taps = 2000
    dense_ir = {
        "metadata": {"sample_rate": sample_rate, "rays_cast": 1, "rays_received": n_taps, "room_name": "Dense"},
        "hits": {
            "delays_seconds": rng.uniform(0.0, 0.5, n_taps).tolist(),
            "pressures": rng.uniform(0.1, 1.0, n_taps).tolist(),
        },
    }
    ir_raw = build_impulse_response(
        dense_ir["hits"]["delays_seconds"], dense_ir["hits"]["pressures"], sample_rate
    )
    nyq = sample_rate / 2.0

    def hf_ratio(x: np.ndarray) -> float:
        sos = signal.butter(4, 2000 / nyq, btype="highpass", output="sos")
        hf = signal.sosfiltfilt(sos, x)
        return float(np.sum(hf**2) / np.sum(x**2))

    carpet = apply_material_absorption(ir_raw, sample_rate, "carpet")
    concrete = apply_material_absorption(ir_raw, sample_rate, "concrete")
    r_carpet, r_concrete = hf_ratio(carpet), hf_ratio(concrete)
    print(f"HF-Anteil  Teppich: {r_carpet:.4f}   Beton: {r_concrete:.4f}")
    assert r_carpet < r_concrete, "Teppich muss Hoehen staerker schlucken als Beton"
    print("material absorption check ok.")

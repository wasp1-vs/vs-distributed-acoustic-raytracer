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

import numpy as np
from scipy import signal


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


def convolve(
    dry_audio: np.ndarray,
    sample_rate: int,
    ir_data: dict,
) -> np.ndarray:
    """Mono-/omnidirektionale Faltung des trockenen Audios mit dem IR aus `ir_data`.

    Etwaige Richtungsdaten (`ir_data["hits"]["directions"]`) werden hier bewusst
    ignoriert. Fuer richtungsabhaengige (binaurale) Faltung siehe
    `binaural_convolver.BinauralConvolver`.

    Args:
        dry_audio: 1D (mono) oder 2D (samples x channels) Audio-Array.
        sample_rate: Sample-Rate von `dry_audio` in Hz; muss zur IR-Metadata passen.
        ir_data: Geparstes JSON-Dict vom Ray-Tracer (Jians Output).
            Erwartetes Schema:
                ir_data["metadata"]["sample_rate"]: int
                ir_data["hits"]["delays_seconds"]: list[float]
                ir_data["hits"]["pressures"]: list[float]

    Returns:
        Raw wet audio als float32-NumPy-Array. Nicht normalisiert -
        Kais' write_wav faengt Clipping ab.
    """
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

import numpy as np
import soundfile as sf

def read_wav(wav_path: str) -> tuple:
    """Reads a WAV file and returns (audio_data, sample_rate)."""
    audio_data, sample_rate = sf.read(wav_path)
    return audio_data, sample_rate

def write_wav(wav_path: str, audio_data, sample_rate: int) -> None:
    """Normalizes audio to prevent clipping and writes to a WAV file."""
    max_amplitude = np.max(np.abs(audio_data))
    # Only normalize when necessary – preserves relative levels between runs
    if max_amplitude > 1.0:
        audio_data = audio_data / max_amplitude
    sf.write(wav_path, audio_data, sample_rate)
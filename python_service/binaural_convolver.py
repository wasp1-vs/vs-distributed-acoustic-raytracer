import numpy as np
from scipy import signal
from hrtf import HRTFDatabase

# Hilfsfunktion
def vector_to_az_el(vec):
    x, y, z = vec
    norm = np.linalg.norm(vec)
    if norm < 1e-8:
        return 0.0, 0.0
    azimuth = np.degrees(np.arctan2(y, x))    # Winkel XY-Ebene
    elevation = np.degrees(np.arcsin(z / norm))  # Winkel Z-Höhe
    return azimuth, elevation

class BinauralConvolver:
    def __init__(self, hrtf_db: HRTFDatabase, sample_rate: int):
        self.hrtf_db = hrtf_db
        self.sample_rate = sample_rate

    def build_binaural_ir(self, delays, pressures, directions):
        max_delay = max(delays)
        ir_length = int(np.ceil((max_delay + 0.1) * self.sample_rate))
        ir_l = np.zeros(ir_length)
        ir_r = np.zeros(ir_length)

        for delay, pressure, direction in zip(delays, pressures, directions):
            az, el = vector_to_az_el(direction)
            hrir_l, hrir_r = self.hrtf_db.get_closest_hrir(az, el)

            idx = int(np.round(delay * self.sample_rate))
            end_idx = idx + len(hrir_l)
            if end_idx > ir_length:
                # Kürzen wenn HRI länger als IR buffer
                hrir_l = hrir_l[:ir_length - idx]
                hrir_r = hrir_r[:ir_length - idx]
                end_idx = ir_length

            ir_l[idx:end_idx] += hrir_l * pressure
            ir_r[idx:end_idx] += hrir_r * pressure

        return np.vstack([ir_l, ir_r]).T  # shape (samples, 2)

    def convolve(self, dry_audio, delays, pressures, directions):
        binaural_ir = self.build_binaural_ir(delays, pressures, directions)

        if dry_audio.ndim == 1:
            out_l = signal.oaconvolve(dry_audio, binaural_ir[:,0], mode='full')
            out_r = signal.oaconvolve(dry_audio, binaural_ir[:,1], mode='full')
            wet = np.stack([out_l, out_r], axis=1)
        elif dry_audio.ndim == 2:
            outs = []
            for c in range(dry_audio.shape[1]):
                out_l = signal.oaconvolve(dry_audio[:,c], binaural_ir[:,0], mode='full')
                out_r = signal.oaconvolve(dry_audio[:,c], binaural_ir[:,1], mode='full')
                outs.append(np.stack([out_l, out_r], axis=1))
            wet = np.concatenate(outs, axis=1)
        else:
            raise ValueError("dry_audio must be 1D or 2D ndarray")

        return wet.astype(np.float32)
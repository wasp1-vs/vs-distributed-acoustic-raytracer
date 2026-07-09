import numpy as np
import pysofaconventions as sofa

class HRTFDatabase:
    def __init__(self, sofa_file_path: str):
        self.sofa = sofa.SOFAFile(sofa_file_path, "r")
        # Positionsdaten: azimuth, elevation, distance (in Grad + m)
        self.positions = self.sofa.getVariableValue('SourcePosition')  # shape (N, 3)
        # HRIR-Daten Shape: (N positions, 2 ears (L/R), samples)
        self.hrir_data = self.sofa.getDataIR()

    def get_closest_hrir(self, azimuth_deg: float, elevation_deg: float):
        """
        Sucht den nächsten Messpunkt in der HRTF-Datenbank anhand Azimut/Elevation.
        Einfaches nearest-neighbor, keine Interpolation.
        """
        angles = self.positions[:, :2]  # Nur azimuth und elevation
        # Abstände berechnen
        dists = np.linalg.norm(angles - np.array([azimuth_deg, elevation_deg]), axis=1)
        idx = np.argmin(dists)
        hrir_l = self.hrir_data[idx, 0, :]  # Linkes Ohr
        hrir_r = self.hrir_data[idx, 1, :]  # Rechtes Ohr
        return hrir_l, hrir_r
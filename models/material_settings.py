import math

from simulation.printing_simulator import SimulationSettings


MATERIALS = {
    'PLA': {'temperature': (190, 230, 210, 5), 'speed': (30, 150, 60, 5), 'layer': (0.10, 0.30, 0.20, 0.05)},
    'PETG': {'temperature': (220, 250, 235, 5), 'speed': (25, 120, 55, 5), 'layer': (0.10, 0.30, 0.20, 0.05)},
    'ABS': {'temperature': (230, 260, 245, 5), 'speed': (25, 110, 50, 5), 'layer': (0.10, 0.30, 0.20, 0.05)},
}


class MaterialSettings(SimulationSettings):
    """Same data interface, with material-aware parameter limits."""

    def __init__(self, material='PLA', **kwargs):
        object.__setattr__(self, 'material', material)
        super().__init__(**kwargs)

    def validate(self):
        if self.material not in MATERIALS:
            raise ValueError('Unbekanntes Druckmaterial.')

        ranges = MATERIALS[self.material]

        for name, value, key in (
            ('Düsentemperatur', self.temperature, 'temperature'),
            ('Druckgeschwindigkeit', self.print_speed, 'speed'),
            ('Schichthöhe', self.layer_height, 'layer'),
        ):
            lo, hi, _, _ = ranges[key]

            if not math.isfinite(value) or not lo - 1e-9 <= value <= hi + 1e-9:
                raise ValueError(
                    f'{name} muss zwischen {lo} und {hi} liegen.'
                )
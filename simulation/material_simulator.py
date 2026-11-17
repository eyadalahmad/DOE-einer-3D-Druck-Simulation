from simulation.printing_simulator import PrintingSimulator
from models.material_settings import MATERIALS


class MaterialSimulator(PrintingSimulator):
    """Educational material-aware extension, without changing the original simulator."""

    def calculate_defects(self):
        s = self.settings
        m = getattr(s, 'material', 'PLA')
        limits = MATERIALS[m]

        tlo, thi, _, _ = limits['temperature']
        slo, shi, _, _ = limits['speed']
        llo, lhi, _, _ = limits['layer']

        tn = (s.temperature - tlo) / (thi - tlo)
        sn = (s.print_speed - slo) / (shi - slo)
        ln = (s.layer_height - llo) / (lhi - llo)

        # Educational response surface, not a physically validated model.
        base = {
            'PLA': (0.06, 0.03),
            'PETG': (0.09, 0.04),
            'ABS': (0.16, 0.05)
        }[m]

        warp = base[0] + 0.27 * tn + 0.10 * ln + 0.10 * tn * ln
        shift = base[1] + 0.42 * sn + 0.12 * ln + 0.08 * sn * ln

        return {
            'warping_mm': round(warp, 4),
            'layer_shifting_mm': round(shift, 4)
        }

    def run(self):
        result = super().run()
        result['settings']['material'] = getattr(
            self.settings, 'material', 'PLA'
        )
        return result
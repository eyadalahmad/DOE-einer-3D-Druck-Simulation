
from itertools import product
from math import ceil

import pandas as pd

from models.material_settings import MATERIALS, MaterialSettings
from simulation.material_simulator import MaterialSimulator


class DOEAnalyzer:
    """Full factorial 2^3 educational DOE with center runs."""

    def __init__(self, material, center_repeats=3):
        self.material = material
        self.center_repeats = center_repeats
        self.profile = MATERIALS[material]

    def factor_levels(self):
        rows = []
        for label, key in [
            ('Düsentemperatur (°C)', 'temperature'),
            ('Druckgeschwindigkeit (mm/s)', 'speed'),
            ('Schichthöhe (mm)', 'layer'),
        ]:
            lo, hi, _, _ = self.profile[key]
            rows.append({
                'Faktor': label,
                'Low (-1)': lo,
                'Center (0)': round((lo + hi) / 2, 3),
                'High (+1)': hi,
            })
        return rows

    def _run(self, temperature, speed, layer_height):
        settings = MaterialSettings(
            material=self.material,
            temperature=float(temperature),
            print_speed=float(speed),
            layer_height=float(layer_height),
        )
        simulator = MaterialSimulator(
            width=20, depth=20, height=20,
            settings=settings, cad_model=None,
        )
        defects = simulator.calculate_defects()
        return {
            'Material': self.material,
            'Temperatur (°C)': temperature,
            'Geschwindigkeit (mm/s)': speed,
            'Schichthöhe (mm)': layer_height,
            'Qualität': simulator.calculate_quality(),
            'Warping (mm)': defects['warping_mm'],
            'Layer Shifting (mm)': defects['layer_shifting_mm'],
            'Anzahl der Schichten': ceil(20 / float(layer_height)),
        }

    def calculate(self):
        records = []
        p = self.profile

        for idx, levels in enumerate(
            product((-1, 1), repeat=3), start=1
        ):
            vals = []
            for level, key in zip(
                levels, ('temperature', 'speed', 'layer')
            ):
                low, high, _, _ = p[key]
                vals.append(low if level == -1 else high)

            record = self._run(*vals)
            record.update({
                'Versuch': idx,
                'A': levels[0],
                'B': levels[1],
                'C': levels[2],
                'Typ': 'Faktoriell',
            })
            records.append(record)

        centers = [
            (p[key][0] + p[key][1]) / 2
            for key in ('temperature', 'speed', 'layer')
        ]

        for _ in range(self.center_repeats):
            record = self._run(*centers)
            record.update({
                'Versuch': len(records) + 1,
                'A': 0, 'B': 0, 'C': 0,
                'Typ': 'Mittelpunkt',
            })
            records.append(record)

        return pd.DataFrame(records)

    @staticmethod
    def main_effects(factorial, response):
        effects = []
        for factor, name in [
            ('A', 'Temperatur'),
            ('B', 'Druckgeschwindigkeit'),
            ('C', 'Schichthöhe'),
        ]:
            effect = (
                factorial.loc[factorial[factor] == 1, response].mean()
                - factorial.loc[factorial[factor] == -1, response].mean()
            )
            effects.append({
                'Faktor': name,
                'Effekt (High - Low)': round(float(effect), 5),
            })
        return effects

    @staticmethod
    def interactions(factorial, response):
        interactions = []
        for a, b in [('A', 'B'), ('A', 'C'), ('B', 'C')]:
            signs = factorial[a] * factorial[b]
            effect = (
                factorial.loc[signs == 1, response].mean()
                - factorial.loc[signs == -1, response].mean()
            )
            interactions.append({
                'Wechselwirkung': f'{a} × {b}',
                'Effekt': round(float(effect), 5),
            })
        return interactions

    @staticmethod
    def center_difference(df, factorial, response):
        center = df.loc[df['Typ'] == 'Mittelpunkt', response]
        if center.empty:
            return None
        return center.mean() - factorial[response].mean()

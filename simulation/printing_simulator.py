
from dataclasses import dataclass
import math

import cadquery as cq
import trimesh

from geometry.model_slicer import ModelSlicer


@dataclass(frozen=True)
class SimulationSettings:
    temperature: float = 210.0
    print_speed: float = 60.0
    layer_height: float = 0.2

    def validate(self):
        if not 180 <= self.temperature <= 260:
            raise ValueError(
                "Temperature must be between 180 and 260 °C."
            )

        if not 20 <= self.print_speed <= 200:
            raise ValueError(
                "Print speed must be between 20 and 200 mm/s."
            )

        if not 0.08 <= self.layer_height <= 0.32:
            raise ValueError(
                "Layer height must be between 0.08 and 0.32 mm."
            )


@dataclass(frozen=True)
class PrintLayer:
    index: int
    z_bottom: float
    z_top: float
    x_shift: float
    y_shift: float
    warping_mm: float


class PrintingSimulator:
    """
    Simplified, deterministic educational 3D-printing model.

    Supports:
    - A calibration cube using width, depth and height.
    - A CadQuery CAD model sliced into layers.
    - An STL mesh represented by trimesh.Trimesh.

    Warping and layer shifting are illustrative and are not
    physically validated predictions.
    """

    def __init__(
        self,
        width=20.0,
        depth=20.0,
        height=20.0,
        settings=None,
        cad_model=None,
    ):
        self.settings = settings or SimulationSettings()
        self.settings.validate()

        self.cad_model = cad_model
        self.cad_slices = None

        if isinstance(cad_model, cq.Workplane):
            solids = cad_model.solids().vals()

            if not solids:
                raise ValueError(
                    "CAD model contains no solid."
                )

            if any(not solid.isValid() for solid in solids):
                raise ValueError(
                    "CAD model contains invalid geometry."
                )

            # Use the bounding boxes of all CAD solids.
            bounds = [solid.BoundingBox() for solid in solids]

            self.width = float(
                max(box.xmax for box in bounds)
                - min(box.xmin for box in bounds)
            )

            self.depth = float(
                max(box.ymax for box in bounds)
                - min(box.ymin for box in bounds)
            )

            self.height = float(
                max(box.zmax for box in bounds)
                - min(box.zmin for box in bounds)
            )

            self.model_type = "cad"

        elif isinstance(cad_model, trimesh.Trimesh):
            if (
                cad_model.is_empty
                or not cad_model.is_watertight
                or not cad_model.is_volume
            ):
                raise ValueError(
                    "STL mesh must be a valid closed volume."
                )

            self.width, self.depth, self.height = (
                float(value) for value in cad_model.extents
            )

            self.model_type = "stl"

        elif cad_model is None:
            self.width = float(width)
            self.depth = float(depth)
            self.height = float(height)

            self.model_type = "calibration_cube"

        else:
            raise TypeError(
                "Model must be CadQuery Workplane, "
                "Trimesh or None."
            )

        if min(self.width, self.depth, self.height) <= 0:
            raise ValueError(
                "Model dimensions must be positive."
            )

    @staticmethod
    def _clamp(value, minimum=0.0, maximum=1.0):
        return max(minimum, min(maximum, value))

    def calculate_defects(self):
        s = self.settings

        # Educational assumptions:
        # - Higher temperature increases warping tendency.
        # - Higher speed increases layer-shifting tendency.
        # - Larger layer height slightly increases both tendencies.

        temperature_factor = self._clamp(
            (s.temperature - 200.0) / 30.0
        )

        speed_factor = self._clamp(
            (s.print_speed - 50.0) / 50.0
        )

        layer_factor = self._clamp(
            (s.layer_height - 0.1) / 0.2
        )

        warping_mm = round(
            0.05
            + 0.65 * temperature_factor
            + 0.15 * layer_factor,
            4,
        )

        shifting_mm = round(
            0.02
            + 0.65 * speed_factor
            + 0.10 * layer_factor,
            4,
        )

        return {
            "warping_mm": warping_mm,
            "layer_shifting_mm": shifting_mm,
        }

    def _prepare_cad_slices(self):
        """
        Slice the CAD or STL model only once.

        Slices are cached for subsequent simulation calls.
        """

        if self.cad_model is None:
            return None

        if self.cad_slices is None:
            slicer = ModelSlicer(
                model=self.cad_model,
                layer_height=self.settings.layer_height,
            )

            self.cad_slices = slicer.slice_model()

            if not self.cad_slices:
                raise ValueError(
                    "CAD slicing produced no printable layers."
                )

        return self.cad_slices

    def generate_layers(self):
        defects = self.calculate_defects()

        if self.cad_model is not None:
            cad_slices = self._prepare_cad_slices()

            layer_ranges = [
                (
                    cad_slice.index,
                    cad_slice.z_bottom,
                    cad_slice.z_top,
                )
                for cad_slice in cad_slices
            ]

        else:
            layer_count = math.ceil(
                self.height / self.settings.layer_height
            )

            layer_ranges = [
                (
                    index,
                    index * self.settings.layer_height,
                    min(
                        (index + 1)
                        * self.settings.layer_height,
                        self.height,
                    ),
                )
                for index in range(layer_count)
            ]

        layers = []
        total_layers = len(layer_ranges)

        for position, (
            index,
            z_bottom,
            z_top,
        ) in enumerate(layer_ranges):

            progress = position / max(total_layers - 1, 1)

            # Gradual shift of the upper section.
            shift_progress = self._clamp(
                (progress - 0.55) / 0.15
            )

            x_shift = (
                defects["layer_shifting_mm"]
                * shift_progress
            )

            # Warping concentrated near the print bed.
            warping = (
                defects["warping_mm"]
                * ((1.0 - progress) ** 3)
            )

            layers.append(
                PrintLayer(
                    index=index,
                    z_bottom=round(z_bottom, 6),
                    z_top=round(z_top, 6),
                    x_shift=round(x_shift, 6),
                    y_shift=0.0,
                    warping_mm=round(warping, 6),
                )
            )

        return layers

    def calculate_print_time(self):
        """
        Simplified print-time estimate.

        Calibration cube:
            Original perimeter and infill approximation.

        CAD and STL models:
            Approximation based on actual model volume,
            20% infill and a 0.4 mm extrusion width.

        This is not a G-code time estimate.
        """

        s = self.settings

        if self.cad_model is not None:
            if isinstance(self.cad_model, trimesh.Trimesh):
                volume_mm3 = float(self.cad_model.volume)

            else:
                solids = self.cad_model.solids().vals()

                volume_mm3 = sum(
                    solid.Volume()
                    for solid in solids
                )

            # Simplified effective material volume.
            effective_volume = volume_mm3 * 0.20

            extrusion_width = 0.4

            cross_section = (
                extrusion_width * s.layer_height
            )

            if cross_section <= 0:
                raise ValueError(
                    "Invalid extrusion cross-section."
                )

            path_length = (
                effective_volume / cross_section
            )

            seconds = path_length / s.print_speed

            return round(seconds / 60.0, 2)

        layer_count = math.ceil(
            self.height / s.layer_height
        )

        perimeter_length = 2 * (
            self.width + self.depth
        )

        wall_path = perimeter_length * 2

        infill_area = max(
            0.0,
            (self.width - 1.6)
            * (self.depth - 1.6)
        )

        infill_path = (
            infill_area * 0.2 / 0.4
        )

        path_per_layer = wall_path + infill_path

        seconds = (
            layer_count
            * path_per_layer
            / s.print_speed
        )

        return round(seconds / 60.0, 2)

    def calculate_quality(self):
        defects = self.calculate_defects()

        warping_penalty = (
            defects["warping_mm"] / 0.85
        ) * 45.0

        shifting_penalty = (
            defects["layer_shifting_mm"] / 0.77
        ) * 45.0

        score = max(
            0.0,
            100.0
            - warping_penalty
            - shifting_penalty
        )

        return round(score, 2)

    def run(self):
        layers = self.generate_layers()

        result = {
            "model_type": self.model_type,
            "dimensions_mm": {
                "width": self.width,
                "depth": self.depth,
                "height": self.height,
            },
            "settings": {
                "temperature": self.settings.temperature,
                "print_speed": self.settings.print_speed,
                "layer_height": self.settings.layer_height,
            },
            "layer_count": len(layers),
            "layers": layers,
            "defects": self.calculate_defects(),
            "estimated_print_time_min": (
                self.calculate_print_time()
            ),
            "quality_score": self.calculate_quality(),
        }

        if self.cad_model is not None:
            result["cad_slices"] = self.cad_slices
            result["cad_model"] = self.cad_model

        return result

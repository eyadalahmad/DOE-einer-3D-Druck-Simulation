import math
from dataclasses import dataclass

import cadquery as cq
import numpy as np
import trimesh


@dataclass
class CADSlice:
    index: int
    z_bottom: float
    z_top: float
    model: cq.Workplane | None = None
    mesh_vertices: np.ndarray | None = None
    mesh_faces: np.ndarray | None = None


class ModelSlicer:
    MAX_LAYERS = 5000

    def __init__(self, model, layer_height=0.2):
        if not isinstance(model, (cq.Workplane, trimesh.Trimesh)):
            raise TypeError(
                "Das Modell muss ein CadQuery Workplane "
                "oder ein Trimesh sein."
            )

        if (
            isinstance(layer_height, bool)
            or not isinstance(layer_height, (int, float))
            or not math.isfinite(layer_height)
            or layer_height <= 0
        ):
            raise ValueError("Die Schichthöhe muss positiv sein.")

        self.model = model
        self.layer_height = float(layer_height)

        if isinstance(model, cq.Workplane):
            solids = model.solids().vals()

            if not solids or any(not solid.isValid() for solid in solids):
                raise ValueError(
                    "Das CAD-Modell enthält keinen gültigen Volumenkörper."
                )

            bounds = [solid.BoundingBox() for solid in solids]
            self.z_min = min(float(box.zmin) for box in bounds)
            self.z_max = max(float(box.zmax) for box in bounds)

        else:
            if model.is_empty or not np.isfinite(model.vertices).all():
                raise ValueError("Das STL-Modell enthält ungültige Geometrie.")

            if not model.is_watertight or not model.is_volume:
                raise ValueError(
                    "Das STL-Modell muss ein geschlossenes "
                    "Volumen mit gültiger Orientierung enthalten."
                )

            self.z_min = float(model.bounds[0, 2])
            self.z_max = float(model.bounds[1, 2])

        self.height = self.z_max - self.z_min

        if self.height <= 0:
            raise ValueError("Das CAD-Modell hat keine positive Höhe.")

        self.layer_count = max(
            1,
            math.ceil((self.height - 1e-6) / self.layer_height)
        )

        if self.layer_count > self.MAX_LAYERS:
            raise ValueError(
                "Zu viele Druckschichten. "
                "Bitte eine größere Schichthöhe wählen."
            )

    @staticmethod
    def _clip_polygon(polygon, plane, keep_above):
        if len(polygon) == 0:
            return []
        result = []
        previous = polygon[-1]
        previous_inside = previous[2] >= plane if keep_above else previous[2] <= plane
        for current in polygon:
            current_inside = current[2] >= plane if keep_above else current[2] <= plane
            if current_inside != previous_inside:
                dz = current[2] - previous[2]
                if abs(dz) > 1e-14:
                    t = (plane - previous[2]) / dz
                    result.append(previous + t * (current - previous))
            if current_inside:
                result.append(current)
            previous, previous_inside = current, current_inside
        return result

    def slice_model(self):
        """Return triangle-clipped visual slices; retain genuine empty levels."""
        if isinstance(self.model, trimesh.Trimesh):
            triangles = np.asarray(
                self.model.triangles,
                dtype=np.float64
            )

            if len(triangles) == 0:
                raise ValueError(
                    "Das STL-Modell enthält keine Dreiecke."
                )

        else:
            triangle_groups = []

            for solid in self.model.solids().vals():
                vertices, faces = solid.tessellate(0.12, 0.20)

                if not vertices or not faces:
                    continue

                xyz = np.asarray(
                    [(v.x, v.y, v.z) for v in vertices],
                    dtype=np.float64
                )

                indices = np.asarray(faces, dtype=np.int32)
                triangle_groups.append(xyz[indices])

            if not triangle_groups:
                raise ValueError(
                    "CAD-Tessellierung hat keine Dreiecke geliefert."
                )

            triangles = np.concatenate(
                triangle_groups,
                axis=0
            )
        z_low = triangles[:, :, 2].min(axis=1)
        z_high = triangles[:, :, 2].max(axis=1)
        layers = []
        for index in range(self.layer_count):
            bottom = self.z_min + index * self.layer_height
            top = min(bottom + self.layer_height, self.z_max)
            # Triangles on an exact boundary are included in only one slab.
            candidates = triangles[(z_high >= bottom - 1e-9) &
                                   (z_low <= top + 1e-9)]
            vertices_out = []
            faces_out = []
            for triangle in candidates:
                polygon = self._clip_polygon(list(triangle), bottom, True)
                polygon = self._clip_polygon(polygon, top, False)
                if len(polygon) < 3:
                    continue
                origin = len(vertices_out)
                vertices_out.extend(polygon)
                for j in range(1, len(polygon) - 1):
                    a, b, c = polygon[0], polygon[j], polygon[j + 1]
                    if np.linalg.norm(np.cross(b - a, c - a)) > 1e-12:
                        faces_out.append((origin, origin + j, origin + j + 1))
            if not faces_out:
                # A genuinely empty level is not represented as printed material.
                continue
            layers.append(CADSlice(
                index=index, z_bottom=round(bottom, 6), z_top=round(top, 6),
                mesh_vertices=np.asarray(vertices_out, dtype=np.float32),
                mesh_faces=np.asarray(faces_out, dtype=np.int32),
            ))
        return layers
\
import numpy as np
import trimesh


class MeshValidator:
    """Validate mesh geometry before 3D printing simulation."""

    @staticmethod
    def validate(mesh):
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError("Expected a trimesh.Trimesh object.")

        if mesh.is_empty:
            return {
                "valid": False,
                "printable": False,
                "issues": ["Mesh is empty."],
                "warnings": [],
            }

        issues = []
        warnings = []

        if not np.isfinite(mesh.vertices).all():
            issues.append(
                "Mesh contains invalid vertex coordinates."
            )

        if not mesh.is_watertight:
            issues.append("Mesh is not watertight.")

        if not mesh.is_winding_consistent:
            issues.append("Face winding is inconsistent.")

        if not mesh.is_volume:
            issues.append(
                "Mesh does not define a valid positive volume."
            )

        body_count = int(mesh.body_count)

        if body_count != 1:
            if body_count > 1:
                warnings.append(
                    f"Mesh contains {body_count} disconnected bodies."
                )
            else:
                issues.append(
                    "Mesh contains no valid connected body."
                )

        extents = mesh.extents

        if (
            not np.isfinite(extents).all()
            or np.any(extents <= 0)
        ):
            issues.append("Mesh has invalid dimensions.")

        # Validate disconnected components individually.
        if body_count > 1 and not issues:
            components = mesh.split(only_watertight=False)

            for index, component in enumerate(components, start=1):
                if (
                    component.is_empty
                    or not component.is_watertight
                    or not component.is_winding_consistent
                    or not component.is_volume
                ):
                    issues.append(
                        f"Disconnected body {index} "
                        "is not a valid closed volume."
                    )

        return {
            "valid": len(issues) == 0,
            "printable": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "watertight": bool(mesh.is_watertight),
            "winding_consistent": bool(mesh.is_winding_consistent),
            "volume_mm3": float(mesh.volume),
            "dimensions_mm": extents.tolist(),
            "faces": int(len(mesh.faces)),
        }

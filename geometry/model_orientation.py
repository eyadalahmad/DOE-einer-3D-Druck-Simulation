
import numpy as np
import trimesh


class ModelOrientation:
    """Orient and position an STL model for educational 3D printing."""

    @staticmethod
    def transform(mesh, rotation_x=0, rotation_y=0, rotation_z=0):
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError("Expected a Trimesh model.")

        result = mesh.copy()

        # Apply rotations in X, Y, Z order.
        for axis, angle in (
            ([1, 0, 0], rotation_x),
            ([0, 1, 0], rotation_y),
            ([0, 0, 1], rotation_z),
        ):
            if angle:
                matrix = trimesh.transformations.rotation_matrix(
                    np.radians(angle), axis
                )
                result.apply_transform(matrix)

        # Center the model on the printing bed.
        bounds = result.bounds

        center_x = (bounds[0, 0] + bounds[1, 0]) / 2
        center_y = (bounds[0, 1] + bounds[1, 1]) / 2
        min_z = bounds[0, 2]

        result.apply_translation(
            [-center_x, -center_y, -min_z]
        )

        return result


    @staticmethod
    def suggest_rotation(mesh):
        """Suggest a print orientation based on bottom contact area."""
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError("Expected a Trimesh model.")

        candidates = (
            (0, 0, 0),
            (90, 0, 0),
            (180, 0, 0),
            (270, 0, 0),
            (0, 90, 0),
            (0, 270, 0),
        )

        best_rotation = candidates[0]
        best_area = -1.0

        for rotation in candidates:
            oriented = ModelOrientation.transform(mesh, *rotation)

            bottom_z = oriented.bounds[0, 2]
            tolerance = max(0.5, 0.005 * oriented.extents[2])

            near_bed = (
                oriented.triangles_center[:, 2]
                <= bottom_z + tolerance
            )
            facing_down = oriented.face_normals[:, 2] < -0.9

            contact_area = float(
                np.sum(
                    oriented.area_faces[near_bed & facing_down]
                )
            )

            if contact_area > best_area:
                best_area = contact_area
                best_rotation = rotation

        return best_rotation

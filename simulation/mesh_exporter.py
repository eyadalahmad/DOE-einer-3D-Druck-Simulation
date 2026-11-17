from io import BytesIO

import numpy as np
import trimesh

from simulation.printing_visualizer import PrintingVisualizer


class MeshExporter:
    """
    Export the final geometry of an educational
    3D-printing simulation.
    """

    @staticmethod
    def build_mesh(simulation_result):
        dimensions = simulation_result["dimensions_mm"]
        layers = simulation_result["layers"]

        vertices_list = []
        faces_list = []

        for layer in layers:
            vertices, faces = PrintingVisualizer._layer_mesh(
                layer=layer,
                width=dimensions["width"],
                depth=dimensions["depth"],
                deformation_scale=1.0,
            )

            offset = sum(
                len(item) for item in vertices_list
            )

            vertices_list.append(vertices)
            faces_list.append(faces + offset)

        if not vertices_list:
            raise ValueError("Keine Druckschichten vorhanden.")

        vertices = np.vstack(vertices_list)
        faces = np.vstack(faces_list)

        mesh = trimesh.Trimesh(
            vertices=vertices,
            faces=faces,
            process=False,
        )

        return mesh

    @classmethod
    def export_glb(cls, simulation_result):
        mesh = cls.build_mesh(simulation_result)
        return mesh.export(file_type="glb")

    @classmethod
    def export_stl(cls, simulation_result):
        mesh = cls.build_mesh(simulation_result)
        return mesh.export(file_type="stl")

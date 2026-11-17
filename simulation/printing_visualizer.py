from collections import OrderedDict

from matplotlib import scale
import numpy as np
import plotly.graph_objects as go
import trimesh


class PrintingVisualizer:
    _mesh_cache = OrderedDict()
    _cache_limit = 12
    _cad_tolerance = 0.20
    _cad_angular_tolerance = 0.20

    @staticmethod
    def _layer_mesh(layer, width, depth, deformation_scale=1.0):
        half_w, half_d = width / 2.0, depth / 2.0
        xy = np.array([
            [-half_w, -half_d], [0, -half_d], [half_w, -half_d],
            [half_w, 0], [half_w, half_d], [0, half_d],
            [-half_w, half_d], [-half_w, 0], [0, 0],
        ], dtype=float)
        corner_weights = np.array(
            [1, .25, 1, .25, 1, .25, 1, .25, 0], dtype=float
        )
        warp = layer.warping_mm * deformation_scale
        bottom = np.column_stack((
            xy[:, 0] + layer.x_shift * deformation_scale,
            xy[:, 1] + layer.y_shift * deformation_scale,
            layer.z_bottom + warp * corner_weights,
        ))
        top = np.column_stack((
            xy[:, 0] + layer.x_shift * deformation_scale,
            xy[:, 1] + layer.y_shift * deformation_scale,
            layer.z_top + warp * corner_weights,
        ))
        faces = []
        for j in range(8):
            nxt = (j + 1) % 8
            faces.extend((
                [8, nxt, j],
                [17, 9 + j, 9 + nxt],
                [j, nxt, 9 + nxt],
                [j, 9 + nxt, 9 + j],
            ))
        return np.vstack((bottom, top)), np.asarray(faces, dtype=np.int32)

    @classmethod
    def _original_cad_mesh(cls, cad_model):
        solids = cad_model.solids().vals()
        key = (id(cad_model), tuple(s.hashCode() for s in solids))
        if key in cls._mesh_cache:
            cls._mesh_cache.move_to_end(key)
            return cls._mesh_cache[key]

        vertex_chunks, face_chunks = [], []
        offset = 0

        for solid in solids:
            vertices, faces = solid.tessellate(
                cls._cad_tolerance,
                cls._cad_angular_tolerance,
            )
            if not vertices or not faces:
                continue

            xyz = np.asarray(
                [(v.x, v.y, v.z) for v in vertices],
                dtype=np.float64,
            )
            triangles = np.asarray(faces, dtype=np.int32)
            vertex_chunks.append(xyz)
            face_chunks.append(triangles + offset)
            offset += len(xyz)

        if not vertex_chunks:
            raise ValueError(
                'CAD model contains no displayable triangles.'
            )

        result = (
            np.concatenate(vertex_chunks),
            np.concatenate(face_chunks),
        )
        cls._mesh_cache[key] = result

        while len(cls._mesh_cache) > cls._cache_limit:
            cls._mesh_cache.popitem(last=False)

        return result

    @classmethod
    def _original_stl_mesh(cls, mesh):
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError('STL preview requires a Trimesh model.')

        key = ('stl', id(mesh))

        if key in cls._mesh_cache:
            cls._mesh_cache.move_to_end(key)
            return cls._mesh_cache[key]

        if mesh.is_empty or not len(mesh.faces):
            raise ValueError(
                'STL model contains no displayable triangles.'
            )

        result = (
            np.asarray(mesh.vertices, dtype=np.float64).copy(),
            np.asarray(mesh.faces, dtype=np.int32).copy(),
        )

        cls._mesh_cache[key] = result

        while len(cls._mesh_cache) > cls._cache_limit:
            cls._mesh_cache.popitem(last=False)

        return result

    @staticmethod
    def _clip_at_height(vertices, faces, height):
        """Clip original surface triangles against z<=height, without caps.

        Keeping the original surface (not artificial per-layer top/bottom
        faces) prevents z-fighting and preserves hollow interiors.
        """
        triangles = vertices[faces]
        below = triangles[:, :, 2] <= height + 1e-8
        all_below = below.all(axis=1)
        crosses = below.any(axis=1) & ~all_below
        full_faces = faces[all_below]
        used = []
        partial_faces = []

        for triangle in triangles[crosses]:
            polygon = []
            prev = triangle[-1]
            prev_inside = prev[2] <= height

            for current in triangle:
                inside = current[2] <= height
                if inside != prev_inside:
                    t = (
                        (height - prev[2])
                        / (current[2] - prev[2])
                    )
                    polygon.append(
                        prev + t * (current - prev)
                    )
                if inside:
                    polygon.append(current)
                prev, prev_inside = current, inside

            if len(polygon) < 3:
                continue

            start = len(vertices) + len(used)
            used.extend(polygon)

            for j in range(1, len(polygon) - 1):
                a, b, c = (
                    polygon[0],
                    polygon[j],
                    polygon[j + 1],
                )
                if np.linalg.norm(
                    np.cross(b - a, c - a)
                ) > 1e-10:
                    partial_faces.append([
                        start,
                        start + j,
                        start + j + 1,
                    ])

        if not len(full_faces) and not partial_faces:
            return (
                np.empty((0, 3)),
                np.empty((0, 3), dtype=np.int32),
            )

        all_vertices = (
            np.vstack([vertices, np.asarray(used)])
            if used else vertices
        )
        all_faces = (
            np.vstack([
                full_faces,
                np.asarray(partial_faces, dtype=np.int32),
            ])
            if partial_faces else full_faces
        )

        # Compact vertices for responsiveness in the browser.
        unique, inverse = np.unique(
            all_faces.reshape(-1),
            return_inverse=True,
        )
        return (
            all_vertices[unique].copy(),
            inverse.reshape(-1, 3).astype(np.int32),
        )


    @staticmethod
    def _refine_bottom_surface(vertices, faces):
        """Refine small STL meshes consistently for visual warping."""
        if not len(vertices) or not len(faces):
            return vertices, faces

        # Avoid excessive geometry growth for large STL models.
        max_faces = 5000

        if len(faces) > max_faces:
            return vertices, faces

        xyz = np.asarray(vertices, dtype=np.float64).copy()
        triangles = np.asarray(faces, dtype=np.int32).copy()

        # Subdivide all triangles consistently to avoid T-junctions
        # between the bottom surface and adjacent walls.
        xyz, triangles = trimesh.remesh.subdivide(
            xyz,
            triangles,
        )

        return xyz, triangles


    @staticmethod
    def _apply_defects(vertices, layers, scale, bounds, shift_override=None):
        if not len(vertices):
            return vertices

        xyz = vertices.copy()
        z = xyz[:, 2].copy()
        heights = np.asarray(
            [layer.z_top for layer in layers], dtype=float
        )
        shifts = np.asarray(
            [layer.x_shift for layer in layers], dtype=float
        )
        warps = np.asarray(
            [layer.warping_mm for layer in layers], dtype=float
        )

        # Smooth interpolation avoids discontinuities in large triangles.
        shift = np.interp(
            z, heights, shifts,
            left=shifts[0], right=shifts[-1],
        )
        if shift_override is not None:
            shift = np.full_like(z, shift_override)

        warp = np.interp(
            z, heights, warps,
            left=warps[0], right=warps[-1],
        )

        xmin, xmax, ymin, ymax = bounds
        cx, cy = (
            (xmin + xmax) / 2,
            (ymin + ymax) / 2,
        )
        rx = max((xmax - xmin) / 2, 1e-6)
        ry = max((ymax - ymin) / 2, 1e-6)

        edge = np.clip(
            np.maximum(
                np.abs((xyz[:, 0] - cx) / rx),
                np.abs((xyz[:, 1] - cy) / ry),
            ),
            0, 1,
        ) ** 2


        # Warping is concentrated near the printing bed.
        # The effect gradually decreases toward upper layers.
        # Educational visualization: warping is strongest near the bed.
        bed_z = float(layers[0].z_bottom)
        print_height = max(
            float(layers[-1].z_top) - bed_z,
            1e-6,
        )

        relative_height = np.maximum(z - bed_z, 0.0)

        height_factor = np.exp(
            -relative_height / (0.12 * print_height)
        )

        warp_displacement = scale * warp * edge * height_factor

        xyz[:, 0] += scale * shift
        xyz[:, 2] += warp_displacement

        return xyz

    @classmethod
    def create_figure(
        cls,
        simulation_result,
        visible_layers=None,
        deformation_scale=5.0,
        max_preview_layers=None,
    ):
        layers = simulation_result['layers']
        dims = simulation_result['dimensions_mm']
        width, depth, height = (
            float(dims[k])
            for k in ('width', 'depth', 'height')
        )
        model_type = simulation_result.get(
            'model_type',
            'calibration_cube',
        )
        count = (
            len(layers)
            if visible_layers is None
            else max(0, min(int(visible_layers), len(layers)))
        )

        vertex_chunks, face_chunks = [], []
        offset = 0

        if model_type in ('cad', 'stl') and count:
            model = simulation_result.get('cad_model')
            if model is None:
                raise ValueError(
                    'CAD/STL preview requires cad_model; '
                    'start a new simulation.'
                )

            if model_type == 'stl':
                original, original_faces = cls._original_stl_mesh(model)
                bounds = model.bounds
                xmin, ymin = bounds[0, 0], bounds[0, 1]
                xmax, ymax = bounds[1, 0], bounds[1, 1]
            else:
                original, original_faces = cls._original_cad_mesh(model)
                # Use the original CAD coordinate system.
                box = model.val().BoundingBox()
                xmin, xmax = box.xmin, box.xmax
                ymin, ymax = box.ymin, box.ymax

            clip_height = float(layers[count - 1].z_top)

            if count == len(layers):
                clip_height = float(np.max(original[:, 2]))

            xyz, faces = cls._clip_at_height(
                original,
                original_faces,
                clip_height
            )
            if model_type == 'stl' and len(faces):
                xyz, faces = cls._refine_bottom_surface(
                    xyz, faces
            )            
            if model_type == 'stl' and len(faces):
                # Split the STL surface at the layer-shift boundary.
                # This prevents large triangles from stretching
                # across the discontinuity.
                split_z = (
                    float(np.min(original[:, 2]))
                    + 0.60 * float(np.ptp(original[:, 2]))
                )
                max_shift = max(
                    (layer.x_shift for layer in layers),
                    default=0.0,
                )

                lower_v, lower_f = cls._clip_at_height(
                    xyz, faces, split_z
                )

                # Reuse the same clipping routine for the upper half
                # by temporarily reversing the Z coordinates.
                flipped = xyz.copy()
                flipped[:, 2] *= -1

                upper_v, upper_f = cls._clip_at_height(
                    flipped, faces, -split_z
                )
                upper_v[:, 2] *= -1

                for part_v, part_f, shift_value in (
                    (lower_v, lower_f, 0.0),
                    (upper_v, upper_f, max_shift),
                ):
                    if not len(part_f):
                        continue

                    part_v = cls._apply_defects(
                        part_v,
                        layers[:count],
                        deformation_scale,
                        (xmin, xmax, ymin, ymax),
                        shift_override=shift_value,
                    )

                    part_offset = sum(
                        len(chunk) for chunk in vertex_chunks
                    )
                    vertex_chunks.append(part_v)
                    face_chunks.append(part_f + part_offset)

            else:
                xyz = cls._apply_defects(
                    xyz,
                    layers[:count],
                    deformation_scale,
                    (xmin, xmax, ymin, ymax),
                )

                if len(faces):
                    vertex_chunks.append(xyz)
                    face_chunks.append(faces)

        elif model_type == 'calibration_cube':
            shift_start = int(len(layers) * 0.60)

            max_x_shift = max(
                (layer.x_shift for layer in layers),
                default=0.0,
            )
            max_y_shift = max(
                (abs(layer.y_shift) for layer in layers),
                default=0.0,
            )

            for position, layer in enumerate(layers[:count]):
                if position < shift_start:
                    display_x_shift = 0.0
                    display_y_shift = 0.0
                else:
                    display_x_shift = max_x_shift
                    display_y_shift = max_y_shift

                display_layer = type(layer)(
                    index=layer.index,
                    z_bottom=layer.z_bottom,
                    z_top=layer.z_top,
                    x_shift=display_x_shift,
                    y_shift=display_y_shift,
                    warping_mm=layer.warping_mm,
                )

                xyz, faces = cls._layer_mesh(
                    display_layer,
                    width,
                    depth,
                    deformation_scale,
                )

                vertex_chunks.append(xyz)
                face_chunks.append(faces + offset)
                offset += len(xyz)

        fig = go.Figure()

        if vertex_chunks:
            vertices = np.concatenate(vertex_chunks)
            faces = np.concatenate(face_chunks)

            fig.add_trace(go.Mesh3d(
                x=vertices[:, 0],
                y=vertices[:, 1],
                z=vertices[:, 2],
                i=faces[:, 0],
                j=faces[:, 1],
                k=faces[:, 2],
                color='#3B82F6',
                opacity=1.0,
                flatshading=False,
                lighting=dict(
                    ambient=.55,
                    diffuse=.8,
                    specular=.2,
                    roughness=.8,
                ),
                hoverinfo='skip',
                showscale=False,
            ))

        if (
            model_type in ('cad', 'stl')
            and simulation_result.get('cad_model') is not None
        ):
            model = simulation_result['cad_model']

            if model_type == 'stl':
                bounds = model.bounds
                min_x, min_y, min_z = bounds[0]
                max_x, max_y, max_z = bounds[1]
            else:
                box = model.val().BoundingBox()
                min_x, max_x = box.xmin, box.xmax
                min_y, max_y = box.ymin, box.ymax
                min_z, max_z = box.zmin, box.zmax

            cx = (min_x + max_x) / 2
            cy = (min_y + max_y) / 2
            bed_z = min_z
            z_range = (min_z, max_z)

        else:
            cx = cy = bed_z = 0.0
            min_x, max_x = -width / 2, width / 2
            min_y, max_y = -depth / 2, depth / 2
            z_range = (0, height)

        bed_x = [
            cx - width * .65,
            cx + width * .65,
        ]
        bed_y = [
            cy - depth * .65,
            cy + depth * .65,
        ]

        fig.add_trace(go.Surface(
            x=np.array([
                [bed_x[0], bed_x[1]],
                [bed_x[0], bed_x[1]],
            ]),
            y=np.array([
                [bed_y[0], bed_y[0]],
                [bed_y[1], bed_y[1]],
            ]),
            z=np.full((2, 2), bed_z),
            colorscale=[
                [0, '#64748B'],
                [1, '#64748B'],
            ],
            opacity=.20,
            showscale=False,
            hoverinfo='skip',
        ))

        margin = max(width, depth, height) * .15 + 2

        fig.update_layout(
            title='Interaktive 3D-Drucksimulation',
            scene=dict(
                xaxis_title='X (mm)',
                yaxis_title='Y (mm)',
                zaxis_title='Z (mm)',
                xaxis=dict(
                    range=[
                        min_x - margin,
                        max_x + margin,
                    ]
                ),
                yaxis=dict(
                    range=[
                        min_y - margin,
                        max_y + margin,
                    ]
                ),
                zaxis=dict(
                    range=[
                        z_range[0] - margin * .1,
                        z_range[1] + margin,
                    ]
                ),
                aspectmode='data',
                camera=dict(
                    eye=dict(x=1.6, y=1.6, z=1.25)
                ),
            ),
            margin=dict(l=0, r=0, t=45, b=0),
            height=750,
            showlegend=False,
            uirevision='printing_camera',
        )
        return fig

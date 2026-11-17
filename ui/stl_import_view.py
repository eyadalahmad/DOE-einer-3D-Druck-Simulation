import numpy as np
import hashlib
from io import BytesIO

import plotly.graph_objects as go
import streamlit as st
import trimesh

from geometry.mesh_validator import MeshValidator
from geometry.model_orientation import ModelOrientation


def render_model_creation(reset_simulation):
    st.header('STL-Modell importieren')
    # STL import and preview.
    with st.expander('STL-Modell importieren', expanded=False):
        uploaded_stl = st.file_uploader(
            'STL-Datei auswählen',
            type=['stl'],
            key='imported_stl_upload',
        )

        if uploaded_stl is not None:
            try:
                raw = uploaded_stl.getvalue()
                digest = hashlib.sha256(raw).hexdigest()

                # Avoid loading the same file again on every rerun.
                if st.session_state.get('imported_stl_digest') != digest:
                    reset_simulation()
                    mesh = trimesh.load(
                        BytesIO(raw),
                        file_type='stl',
                        process=True,
                    )

                    if not isinstance(mesh, trimesh.Trimesh):
                        raise ValueError(
                            'Die Datei enthält kein unterstütztes STL-Dreiecksnetz.'
                        )

                    report = MeshValidator.validate(mesh)

                    st.session_state['imported_stl_original_mesh'] = mesh.copy()
                    suggested_rotation = ModelOrientation.suggest_rotation(mesh)
                    st.session_state['stl_rotation_x'] = suggested_rotation[0]
                    st.session_state['stl_rotation_y'] = suggested_rotation[1]
                    st.session_state['stl_rotation_z'] = suggested_rotation[2]

                    st.session_state['imported_stl_mesh'] = ModelOrientation.transform(
                        mesh,
                        *suggested_rotation,
                    )
                    st.session_state['imported_stl_report'] = report
                    st.session_state['imported_stl_digest'] = digest

                mesh = st.session_state['imported_stl_mesh']
                report = st.session_state['imported_stl_report']
                st.subheader('Modellausrichtung')

                st.caption(
                    'Automatischer Ausrichtungsvorschlag. '
                    'Die Ausrichtung kann vor der Simulation angepasst werden.'
                )

                col_x, col_y, col_z = st.columns(3)

                with col_x:
                    rotation_x = st.selectbox(
                        'Rotation X (°)',
                        [0, 90, 180, 270],
                        key='stl_rotation_x',
                    )

                with col_y:
                    rotation_y = st.selectbox(
                        'Rotation Y (°)',
                        [0, 90, 180, 270],
                        key='stl_rotation_y',
                    )

                with col_z:
                    rotation_z = st.selectbox(
                        'Rotation Z (°)',
                        [0, 90, 180, 270],
                        key='stl_rotation_z',
                    )

                original_mesh = st.session_state['imported_stl_original_mesh']

                oriented_mesh = ModelOrientation.transform(
                    original_mesh,
                    rotation_x,
                    rotation_y,
                    rotation_z,
                )

                previous_mesh = st.session_state['imported_stl_mesh']

                if not np.allclose(
                    previous_mesh.vertices,
                    oriented_mesh.vertices,
                ):
                    reset_simulation()

                st.session_state['imported_stl_mesh'] = oriented_mesh
                mesh = oriented_mesh

                dims = mesh.extents

                st.write(
                    'Abmessungen (STL-Einheiten, üblicherweise mm): '
                    f'{dims[0]:.2f} × {dims[1]:.2f} × {dims[2]:.2f}'
                )

                st.write(
                    f'Dreiecke: {len(mesh.faces):,} · '
                    f'Geschlossene Oberfläche: '
                    f'{"Ja" if mesh.is_watertight else "Nein"}'
                )

                if report['valid']:
                    st.success('Geometrieprüfung bestanden.')
                else:
                    st.warning(
                        'Geometrieprüfung: '
                        + '; '.join(report['issues'])
                    )

                for warning in report.get('warnings', []):
                    st.info(f'Hinweis zur STL-Geometrie: {warning}')

                fig = go.Figure(
                    data=[
                        go.Mesh3d(
                            x=mesh.vertices[:, 0],
                            y=mesh.vertices[:, 1],
                            z=mesh.vertices[:, 2],
                            i=mesh.faces[:, 0],
                            j=mesh.faces[:, 1],
                            k=mesh.faces[:, 2],
                            color='#3B82F6',
                            opacity=1.0,
                        )
                    ]
                )

                fig.update_layout(
                    scene=dict(aspectmode='data'),
                    margin=dict(l=0, r=0, t=30, b=0),
                    height=500,
                )

                st.plotly_chart(
                    fig,
                    width='stretch',
                    key='imported_stl_preview',
                )

                if report['valid']:
                    st.info(
                        'Das STL-Modell kann im Bereich '
                        '3D-Drucksimulation ausgewählt werden.'
                    )
                else:
                    st.info(
                        'Nur STL-Modelle mit bestandener '
                        'Geometrieprüfung können simuliert werden.'
                    )

            except Exception as exc:
                for key in (
                    'imported_stl_mesh',
                    'imported_stl_original_mesh',
                    'imported_stl_report',
                    'imported_stl_digest',
                    'stl_rotation_x',
                    'stl_rotation_y',
                    'stl_rotation_z',
                ):
                    st.session_state.pop(key, None)

                st.error(
                    f'STL-Datei konnte nicht geladen werden: {exc}'
                )

        else:
            if st.session_state.get('imported_stl_digest') is not None:
                reset_simulation()

            for key in (
                'imported_stl_mesh',
                'imported_stl_original_mesh',
                'imported_stl_report',
                'imported_stl_digest',
                'stl_rotation_x',
                'stl_rotation_y',
                'stl_rotation_z',
            ):
                st.session_state.pop(key, None)

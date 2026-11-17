
import csv
from io import StringIO

import streamlit as st

from simulation.printing_visualizer import PrintingVisualizer
from simulation.mesh_exporter import MeshExporter


def render_metrics(result):
    cols = st.columns(4)
    cols[0].metric('Qualitätsbewertung', f'{result["quality_score"]:.1f} / 100')
    cols[1].metric('Warping', f'{result["defects"]["warping_mm"]:.3f} mm')
    cols[2].metric('Layer Shifting', f'{result["defects"]["layer_shifting_mm"]:.3f} mm')
    cols[3].metric('Anzahl der Schichten', f'{result["layer_count"]}')


def history_to_csv(history):
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(['Versuch', 'Zeitpunkt', 'Material', 'Temperatur (C)',
                     'Druckgeschwindigkeit (mm/s)', 'Schichthoehe (mm)',
                     'Qualitaet', 'Warping (mm)', 'Layer Shifting (mm)', 'Anzahl der Schichten'])
    for record in history:
        r = record['result']
        s = r['settings']
        writer.writerow([record['id'], record['date'], s.get('material', 'PLA'),
                         s['temperature'], s['print_speed'], s['layer_height'],
                         r['quality_score'], r['defects']['warping_mm'],
                         r['defects']['layer_shifting_mm'], r['layer_count']])
    return out.getvalue().encode('utf-8-sig')


def render_history(deformation_scale=5.0):
    st.divider()
    left, right = st.columns([3, 1])
    with left:
        st.subheader('Druckhistorie')
    history = st.session_state['print_history']
    with right:
        if st.button('🗑️ Historie löschen', disabled=not history, width='stretch'):
            st.session_state['confirm_clear_history'] = True
    if st.session_state['confirm_clear_history']:
        st.warning('Wirklich alle gespeicherten Druckversuche löschen?')
        a, b = st.columns(2)
        with a:
            if st.button('Ja, alle löschen', type='primary'):
                st.session_state['print_history'] = []
                st.session_state['print_number'] = 0
                st.session_state['confirm_clear_history'] = False
                if st.session_state['print_status'] == 'completed':
                    st.session_state['print_saved'] = True
                st.rerun()
        with b:
            if st.button('Abbrechen'):
                st.session_state['confirm_clear_history'] = False
                st.rerun()
    if not history:
        st.info('Noch keine abgeschlossenen Druckversuche vorhanden.')
        return
    st.write(f'Gespeicherte Druckversuche: {len(history)}')
    rows = []
    for record in history:
        r, s = record['result'], record['result']['settings']
        rows.append({'Versuch': record['id'], 'Zeitpunkt': record['date'],
                     'Material': s.get('material', 'PLA'), 'Temperatur (°C)': s['temperature'],
                     'Geschwindigkeit (mm/s)': s['print_speed'], 'Schichthöhe (mm)': s['layer_height'],
                     'Qualität': r['quality_score'], 'Warping (mm)': r['defects']['warping_mm'],
                     'Shifting (mm)': r['defects']['layer_shifting_mm'],
                     'Anzahl der Schichten': r['layer_count']})
    st.dataframe(rows, width='stretch', hide_index=True)
    st.download_button('📥 Alle Ergebnisse als CSV exportieren', history_to_csv(history),
                       'druckhistorie.csv', 'text/csv', width='stretch')
    selected = st.selectbox('Gespeicherten Druckversuch anzeigen',
                            options=range(len(history)),
                            format_func=lambda i: f'Versuch {history[i]["id"]} – {history[i]["date"]}')
    record = history[selected]
    result = record['result']
    st.caption(f'Darstellung mit Visualisierungsfaktor {deformation_scale:.1f}×.')
    st.plotly_chart(PrintingVisualizer.create_figure(result, deformation_scale=deformation_scale),
                    width='stretch', key=f'history_chart_{record["id"]}')
    render_metrics(result)
    if result.get('model_type') in ('cad', 'stl'):
        st.caption(
            'STL-/GLB-Export für CAD-/STL-Druckschichten '
            'wird später ergänzt.'
        )
        return
    st.subheader('3D-Modell exportieren')
    try:
        glb = MeshExporter.export_glb(result)
        stl = MeshExporter.export_stl(result)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button('📥 GLB herunterladen', glb, f'druckversuch_{record["id"]}.glb',
                               'model/gltf-binary', width='stretch')
        with c2:
            st.download_button('📥 STL herunterladen', stl, f'druckversuch_{record["id"]}.stl',
                               'application/octet-stream', width='stretch')
    except Exception as exc:
        st.error(f'3D-Export fehlgeschlagen: {exc}')

import time

import streamlit as st

from models.material_settings import MATERIALS, MaterialSettings
from simulation.material_simulator import MaterialSimulator
from simulation.printing_visualizer import PrintingVisualizer
from simulation.simulation_state import (
    initialize_state,
    reset_simulation,
    save_completed_print,
)
from ui.history_view import render_metrics, render_history


def render_simulation():
    initialize_state()
    st.header('Interaktive 3D-Drucksimulation')
    st.caption('Didaktisches Modell – keine physikalisch validierte Vorhersage realer Druckfehler.')
    
    imported_mesh = st.session_state.get('imported_stl_mesh')
    imported_report = st.session_state.get('imported_stl_report')

    model_options = ['Kalibrierwürfel']


    if (
        imported_mesh is not None
        and imported_report
        and imported_report.get('valid')
    ):
        model_options.append('Importiertes STL-Modell')

    # Keep the previous selection if it is still available.
    current_source = st.session_state.get(
        'simulation_model_source'
    )

    if current_source not in model_options:
        if current_source is not None:
            reset_simulation()

        if 'Importiertes STL-Modell' in model_options:
            preferred = 'Importiertes STL-Modell'
        else:
            preferred = 'Kalibrierwürfel'

        st.session_state['simulation_model_source'] = preferred

    selected_source = st.selectbox(
        'Modell für die Drucksimulation',
        model_options,
        key='simulation_model_source',
        disabled=st.session_state['print_status'] != 'idle',
        on_change=reset_simulation,
    )

    if selected_source == 'Importiertes STL-Modell':
        cad_model = imported_mesh

        st.success(
            'Das importierte STL-Modell ist '
            'für die Simulation ausgewählt.'
        )

    else:
        cad_model = None

        st.info(
            'Für die Simulation wird '
            'der Kalibrierwürfel verwendet.'
        )


    with st.sidebar:
        st.header('Druckparameter')
        status = st.session_state['print_status']
        material = st.selectbox('Druckmaterial', list(MATERIALS), key='material',
                                disabled=status != 'idle')
        profile = MATERIALS[material]
        tmin, tmax, tdefault, tstep = profile['temperature']
        smin, smax, sdefault, sstep = profile['speed']
        lmin, lmax, ldefault, lstep = profile['layer']
        # Keys are material-specific, so switching material restores its own defaults.
        temperature = st.slider('Düsentemperatur (°C)', tmin, tmax, tdefault, tstep,
                                key=f'temp_{material}', disabled=status != 'idle')
        speed = st.slider('Druckgeschwindigkeit (mm/s)', smin, smax, sdefault, sstep,
                          key=f'speed_{material}', disabled=status != 'idle')
        layer_height = st.slider('Schichthöhe (mm)', lmin, lmax, ldefault, lstep,
                                 format='%.2f', key=f'layer_{material}', disabled=status != 'idle')
        st.divider()
        animation_speed = st.slider('Geschwindigkeit der Animation (Schichten/s)', 1, 50, 10)
        st.divider()
        deformation_scale = st.slider('Visualisierungsfaktor', 1.0, 15.0, 5.0, 0.5,
                                      help='Vergrößert die dargestellten Druckfehler, nicht die Messwerte.')
        st.caption(f'Darstellungsvergrößerung: {deformation_scale:.1f}×')

    refresh = '1s' if st.session_state['print_status'] == 'running' else None

    @st.fragment(run_every=refresh)
    def animation_panel():
        status = st.session_state['print_status']
        a, b, c, d = st.columns(4)
        with a:
            if st.button('▶ Start', disabled=status != 'idle', width='stretch'):
                try:
                    settings = MaterialSettings(material=material, temperature=temperature,
                                                print_speed=speed, layer_height=layer_height)
                    with st.spinner('Druckschichten werden vorbereitet...'):
                        result = MaterialSimulator(width=20, depth=20, height=20,
                                                   settings=settings, cad_model=cad_model).run()
                    st.session_state['print_result'] = result
                    st.session_state['print_layer'] = 0
                    st.session_state['print_status'] = 'running'
                    st.session_state['print_saved'] = False
                    st.session_state['animation_last_tick'] = time.monotonic()
                    st.session_state['animation_fraction'] = 0.0
                    st.rerun()
                except Exception as exc:
                    st.error(f'Drucksimulation konnte nicht gestartet werden: {exc}')
        with b:
            if st.button('⏸ Pause', disabled=status != 'running', width='stretch'):
                st.session_state['print_status'] = 'paused'
                st.session_state['animation_last_tick'] = None
                st.rerun()
        with c:
            if st.button('▶ Resume', disabled=status != 'paused', width='stretch'):
                st.session_state['print_status'] = 'running'
                st.session_state['animation_last_tick'] = time.monotonic()
                st.rerun()
        with d:
            if st.button('↺ Reset', disabled=status == 'idle', width='stretch'):
                reset_simulation()
                st.rerun()

        result = st.session_state['print_result']
        if result is None:
            st.info('Wählen Sie die Druckparameter und klicken Sie auf Start.')
            return
        total = max(1, int(result['layer_count']))
        if status == 'running':
            now = time.monotonic()
            previous = st.session_state.get('animation_last_tick') or now
            elapsed = max(0.0, now - previous)
            st.session_state['animation_last_tick'] = now
            fraction = st.session_state['animation_fraction'] + elapsed * animation_speed
            advance = int(fraction)
            st.session_state['animation_fraction'] = fraction - advance
            st.session_state['print_layer'] = min(total, st.session_state['print_layer'] + advance)
        current = st.session_state['print_layer']
        st.progress(current / total, text=f'Druckfortschritt: {current} / {total} Schichten')
        st.plotly_chart(PrintingVisualizer.create_figure(
            simulation_result=result, visible_layers=current,
            deformation_scale=deformation_scale), width='stretch', key='current_print_chart')
        render_metrics(result)
        if current >= total and status == 'running':
            st.session_state['print_status'] = 'completed'
            st.session_state['animation_last_tick'] = None
            save_completed_print()
            st.rerun()
        if status == 'completed':
            save_completed_print()
            st.success('Drucksimulation abgeschlossen und in der Druckhistorie gespeichert!')

    animation_panel()
    render_history(deformation_scale)

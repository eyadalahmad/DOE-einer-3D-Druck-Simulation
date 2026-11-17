
from datetime import datetime

import streamlit as st


def initialize_state():
    defaults = {
        'print_status': 'idle', 'print_layer': 0, 'print_result': None,
        'print_history': [], 'print_saved': False, 'print_number': 0,
        'confirm_clear_history': False, 'material': 'PLA',
        'animation_last_tick': None, 'animation_fraction': 0.0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_simulation():
    for key, value in {
        'print_status': 'idle', 'print_layer': 0, 'print_result': None,
        'print_saved': False, 'animation_last_tick': None,
        'animation_fraction': 0.0,
    }.items():
        st.session_state[key] = value


def save_completed_print():
    if st.session_state['print_saved'] or st.session_state['print_result'] is None:
        return

    st.session_state['print_number'] += 1
    st.session_state['print_history'].append({
        'id': st.session_state['print_number'],
        'date': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
        'result': st.session_state['print_result'],
    })
    st.session_state['print_saved'] = True

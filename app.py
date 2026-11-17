
import streamlit as st

from ui.doe_view import render_doe
from ui.stl_import_view import render_model_creation
from ui.simulation_view import render_simulation
from simulation.simulation_state import (
    initialize_state,
    reset_simulation,
)


def main():
    st.set_page_config(page_title='3D Printing Quality Simulation', page_icon='🖨️', layout='wide')
    initialize_state()
    st.title('Interaktive Qualitätssimulation im 3D-Druck')
    st.subheader('Prozessoptimierung mittels DOE')
    tab1, tab2, tab3 = st.tabs([
        'STL-Modell importieren',
        '3D-Drucksimulation',
        'DOE Experimente',
    ])
    with tab1:
        render_model_creation(reset_simulation)
    with tab2:
        render_simulation()
    with tab3:
        render_doe()


if __name__ == '__main__':
    main()
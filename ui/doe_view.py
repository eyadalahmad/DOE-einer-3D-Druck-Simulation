
import pandas as pd
import streamlit as st

from models.material_settings import MATERIALS
from doe.doe_analyzer import DOEAnalyzer


def render_doe():
    st.header('DOE – Design of Experiments')
    st.caption(
        'Vollfaktorieller Versuchsplan 2³ mit Mittelpunktversuchen. '
        'Deterministische Lehrmodellwerte, keine experimentellen Messdaten.'
    )

    material = st.selectbox(
        'Material für DOE', list(MATERIALS), key='doe_material'
    )
    center_repeats = st.slider(
        'Wiederholungen im Zentrum', 0, 20, 3,
        key='doe_center_repeats'
    )

    analyzer = DOEAnalyzer(material, center_repeats)

    st.subheader('Faktorstufen')
    st.dataframe(
        analyzer.factor_levels(), hide_index=True, width='stretch'
    )

    st.info(
        f'8 Eckpunkte + {center_repeats} Mittelpunktversuche = '
        f'{8 + center_repeats} Simulationen. Wiederholte Mittelpunkte '
        'liefern im deterministischen Modell keine Messstreuung.'
    )

    current_config = (material, center_repeats)

    if st.button('DOE berechnen', type='primary', width='stretch'):
        try:
            st.session_state['doe_results'] = analyzer.calculate()
            st.session_state['doe_config_result'] = current_config
        except Exception as exc:
            st.error(f'DOE-Berechnung fehlgeschlagen: {exc}')
            return

    df = st.session_state.get('doe_results')

    if df is None:
        return

    if st.session_state.get('doe_config_result') != current_config:
        st.info(
            'Material oder Anzahl der Mittelpunktversuche geändert. '
            'Bitte DOE erneut berechnen.'
        )
        return

    required = {
        'Versuch', 'Material', 'Typ', 'A', 'B', 'C', 'Qualität',
        'Warping (mm)', 'Layer Shifting (mm)', 'Anzahl der Schichten',
        'Temperatur (°C)', 'Geschwindigkeit (mm/s)',
        'Schichthöhe (mm)',
    }

    if not required.issubset(df.columns):
        st.warning(
            'Ältere DOE-Ergebnisse sind nicht kompatibel. '
            'Bitte DOE erneut berechnen.'
        )
        return

    factorial = df.loc[df['Typ'] == 'Faktoriell']

    if len(factorial) != 8:
        st.warning(
            'Der Versuchsplan ist unvollständig. Bitte DOE erneut berechnen.'
        )
        return

    st.caption(
        f'Berechnete Versuche für {material} '
        '(Kalibrierkörper 20 × 20 × 20 mm)'
    )
    st.dataframe(df, hide_index=True, width='stretch')

    st.download_button(
        '📥 DOE als CSV exportieren',
        df.to_csv(index=False).encode('utf-8-sig'),
        'doe_ergebnisse.csv',
        'text/csv',
        width='stretch',
    )

    st.subheader('Haupteffekte')
    response = st.selectbox(
        'Zielgröße',
        ['Qualität', 'Warping (mm)',
         'Layer Shifting (mm)', 'Anzahl der Schichten']
    )

    effects = analyzer.main_effects(factorial, response)
    st.dataframe(effects, hide_index=True, width='stretch')
    st.bar_chart(pd.DataFrame(effects).set_index('Faktor'))

    st.subheader('Zweifaktor-Wechselwirkungen')
    interactions = analyzer.interactions(factorial, response)
    st.dataframe(interactions, hide_index=True, width='stretch')

    difference = analyzer.center_difference(df, factorial, response)

    if difference is not None:
        st.metric(
            'Mittelpunkt − Eckpunktmittel',
            f'{difference:+.4f}'
        )
    else:
        st.caption(
            'Kein Mittelpunktversuch: Krümmungsvergleich entfällt.'
        )

    st.caption(
        'Deskriptive Effekte, kein statistischer Signifikanztest. '
        'Reale Messungen, Randomisierung und Wiederholungen sind '
        'für belastbare Schlussfolgerungen notwendig.'
    )

    best = df.loc[df['Qualität'].idxmax()]
    st.subheader('Beste simulierte Qualität')
    st.write(
        f'Versuch {int(best["Versuch"])}: '
        f'{best["Qualität"]:.1f}/100, '
        f'{best["Temperatur (°C)"]} °C, '
        f'{best["Geschwindigkeit (mm/s)"]} mm/s, '
        f'{best["Schichthöhe (mm)"]:.2f} mm.'
    )

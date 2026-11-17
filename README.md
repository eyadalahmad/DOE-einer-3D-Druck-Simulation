
Interaktive Qualitätssimulation im 3D-Druck
==========================================

Projekt im Modul Qualitätsmanagement
Prozessoptimierung mittels Design of Experiments (DOE)


1. Projektbeschreibung
----------------------

Dieses Projekt ist eine interaktive Anwendung zur Simulation
von Qualitätsabweichungen beim 3D-Druck.

Die Anwendung wurde mit Python und Streamlit entwickelt.

Ziel ist es, den Einfluss verschiedener Druckparameter auf
die Druckqualität zu untersuchen und mithilfe von Design of
Experiments (DOE) auszuwerten.

Die Simulation verwendet ein vereinfachtes didaktisches Modell.
Sie stellt keine physikalisch validierte Vorhersage realer
Druckfehler dar.


2. Funktionen
-------------

- Import und Validierung von STL-Dateien
- 3D-Vorschau importierter Modelle
- Simulation eines Kalibrierwürfels
- Simulation importierter STL-Modelle
- Auswahl der Druckmaterialien PLA, PETG und ABS
- Einstellung von Düsentemperatur, Druckgeschwindigkeit
  und Schichthöhe
- Simulation der Druckschichten
- Start, Pause, Resume und Reset
- Einstellbare Animationsgeschwindigkeit
- Visualisierung von Warping und Layer Shifting
- Berechnung einer Qualitätsbewertung
- Anzeige der Anzahl der Druckschichten
- Druckhistorie mit Ergebnisvergleich
- CSV-Export der Druckhistorie
- STL- und GLB-Export für unterstützte simulierte Kalibrierkörper
  (für importierte STL-Modelle derzeit nicht verfügbar)
- DOE-Experimente mit statistischer Auswertung


3. Projektstruktur
------------------

app.py
    Startpunkt der Streamlit-Anwendung.

models/material_settings.py
    Materialprofile und Validierung der Druckparameter.

simulation/printing_simulator.py
    Grundlegende Berechnung der Drucksimulation.

simulation/material_simulator.py
    Materialabhängige Berechnung der Druckfehler.

simulation/printing_visualizer.py
    Dreidimensionale Darstellung der Druckschichten.

simulation/mesh_exporter.py
    Export von Simulationsergebnissen als STL oder GLB.

simulation/simulation_state.py
    Verwaltung des Simulationszustands und der Druckhistorie.

geometry/model_slicer.py
    Verarbeitung und schichtweise Zerlegung von 3D-Modellen.

geometry/mesh_validator.py
    Prüfung importierter STL-Dateien.

geometry/model_orientation.py
    Vorschlag und Anwendung der Modellausrichtung beim STL-Import.

doe/doe_analyzer.py
    Durchführung und Auswertung der DOE-Experimente.

ui/stl_import_view.py
    Benutzeroberfläche für den STL-Import.

ui/simulation_view.py
    Benutzeroberfläche für die Drucksimulation.

ui/history_view.py
    Anzeige und Export der Druckhistorie.

ui/doe_view.py
    Benutzeroberfläche für die DOE-Auswertung.


4. Installation unter Ubuntu
----------------------------

**Voraussetzungen:**
- Ubuntu Linux
- Python 3.12 (entwickelt mit Python 3.12.3)
- Git
- Internetverbindung für die Installation der Bibliotheken

**Schritt 1: Projekt herunterladen**

Das Projekt über GitLab klonen:

```bash
git clone https://git.i.hawk.de/eyad.alahmad/doe-einer-3d-druck-simulation.git
cd DOE einer 3D-Druck Simulation
```

Alternativ kann das Projekt als ZIP-Datei heruntergeladen und entpackt werden.

**Schritt 2: Virtuelle Python-Umgebung erstellen**

```bash
python3.12 -m venv .venv
```

**Schritt 3: Virtuelle Umgebung aktivieren**

```bash
source .venv/bin/activate
```

**Schritt 4: Benötigte Bibliotheken installieren**

```bash
python -m pip install -r requirements.txt
```

**Schritt 5: Anwendung starten**

```bash
streamlit run app.py
```

Die Anwendung ist anschließend normalerweise unter folgender Adresse erreichbar:

http://localhost:8501

Wird der Port 8502 benötigt (z. B. beim Desktop-Starter), kann die
Anwendung alternativ so gestartet werden:

```bash
streamlit run app.py --server.port=8502
```

Dann ist sie unter http://localhost:8502 erreichbar.

**Anwendung beenden**

Im Terminal `Ctrl + C` drücken.

**Anwendung später erneut starten**

```bash
cd DOE einer 3D-Druck Simulation
source .venv/bin/activate
streamlit run app.py
```

**Hinweis:** Die Anwendung wurde unter Ubuntu mit Python 3.12.3
entwickelt. Die Installation auf Windows wurde noch nicht praktisch getestet.


5. Installation unter Windows
-----------------------------

Voraussetzungen:
- Windows 10 oder Windows 11
- Python 3.12 (64-Bit), mit installiertem Python Launcher (py)
- Internetverbindung für die Installation der Bibliotheken
- Optional: Git, falls das Projekt per git clone heruntergeladen wird

Schritt 1: Projekt herunterladen

Das Projekt von GitLab als ZIP-Datei herunterladen und entpacken
oder mit Git klonen. Anschließend PowerShell im Projektordner
öffnen (dort, wo app.py und requirements.txt liegen).

Schritt 2: Python-Version überprüfen

```powershell
py -3.12 --version
```

Schritt 3: Virtuelle Python-Umgebung erstellen

```powershell
py -3.12 -m venv .venv
```

Schritt 4: Benötigte Bibliotheken installieren

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Schritt 5: Anwendung starten

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Die Anwendung ist normalerweise unter folgender Adresse erreichbar:

http://localhost:8501

Anwendung beenden: Im PowerShell-Fenster Ctrl + C drücken.

Anwendung später erneut starten: PowerShell im Projektordner
öffnen und den Befehl aus Schritt 5 ausführen.

Hinweis: python.exe ist die Python-Programmdatei der virtuellen
Umgebung unter Windows; es muss kein zusätzliches Programm
installiert werden. Eine Aktivierung der virtuellen Umgebung
ist für die oben genannten Befehle nicht erforderlich.

Wichtig: Die Windows-Installation ist bislang nicht getestet.
Insbesondere die Verfügbarkeit der benötigten CadQuery-Version
muss auf dem Zielsystem geprüft werden. Bei Installationsfehlern
bitte die vollständige Fehlermeldung kontrollieren.


6. Simulationsparameter
-----------------------

Unterstützte Materialien:

PLA:
Temperatur: 190 bis 230 °C
Geschwindigkeit: 30 bis 150 mm/s

PETG:
Temperatur: 220 bis 250 °C
Geschwindigkeit: 25 bis 120 mm/s

ABS:
Temperatur: 230 bis 260 °C
Geschwindigkeit: 25 bis 110 mm/s

Schichthöhe:
0,10 bis 0,30 mm

Diese Werte sind didaktische Annahmen und keine
verbindlichen Drucker- oder Materialempfehlungen.


7. Design of Experiments
------------------------

Die DOE-Funktion untersucht den Einfluss der
Druckparameter auf die Qualitätsbewertung,
Warping, Layer Shifting und die Anzahl der Druckschichten.

Die Anwendung unterstützt einen vollfaktoriellen
Versuchsplan mit drei Faktoren und jeweils zwei
Faktorstufen (2^3).

Zusätzlich können Mittelpunktversuche
berücksichtigt werden.

Die Ergebnisse werden tabellarisch dargestellt und als CSV exportiert.
Haupteffekte und Zweifaktor-Wechselwirkungen werden deskriptiv
ausgewertet; es wird kein statistischer Signifikanztest durchgeführt.


8. Hinweise
-----------

Die Simulation dient ausschließlich Lehr- und
Demonstrationszwecken im Qualitätsmanagement.

Die berechneten Qualitätskennzahlen und Druckfehler
basieren auf vereinfachten Modellgleichungen.

Die Ergebnisse dürfen nicht als experimentell
validierte Druckergebnisse interpretiert werden.

Die Druckhistorie wird während der aktuellen
Streamlit-Sitzung verwaltet und nicht dauerhaft
in einer Datenbank gespeichert.

Die Anzahl der Schichten wird aus der Modellhöhe und der
eingestellten Schichthöhe ermittelt.

Der STL-/GLB-Export aus der Druckhistorie ist derzeit nicht
für importierte STL-Modelle verfügbar.

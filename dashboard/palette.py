"""Palette partagée : écran de chronométrage (tarmac, violet = meilleur, vert = progression).

Source unique de vérité pour les couleurs. `theme.py` (Streamlit) et `build_site.py`
(page statique) l'importent tous les deux — sans ça, les deux sorties divergeraient
au premier ajustement.

Aucune dépendance : le générateur de page statique n'a pas besoin de Plotly.
"""

TARMAC = "#14171D"
SURFACE = "#1C2129"
LINE = "#2A303B"
TEXT = "#E9ECF1"
MUTED = "#8B93A1"
PURPLE = "#B36BFF"   # meilleur tour / leader
GREEN = "#2BD46B"    # gain
LOSS = "#FF6B6B"     # places perdues (distinct du rouge de la marque)
RED = "#E10600"      # marque, utilisé une seule fois
FONT = "Titillium Web, Segoe UI, Helvetica, Arial, sans-serif"

TYRES = {"SOFT": "#E8002D", "MEDIUM": "#FFD12E", "HARD": "#E9ECF1",
         "INTERMEDIATE": "#43B02A", "WET": "#0067AD"}

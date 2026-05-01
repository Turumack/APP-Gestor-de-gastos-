"""Tema visual global de la app — tokens de color, fuentes, espaciados.

Colores inspirados en apps fintech modernas (Revolut / Lunch Money / Copilot Money):
- Fondo casi negro con acentos violeta y pink
- Glass morphism en cards
- Tipografía Inter + Space Grotesk
"""

# ── Paleta ─────────────────────────────────────────────
BG = "#0a0a0f"            # fondo base
BG_SOFT = "#14141c"       # tarjetas base
BG_CARD = "rgba(255, 255, 255, 0.04)"   # glass card
BORDER = "rgba(255, 255, 255, 0.08)"
BORDER_SOFT = "rgba(255, 255, 255, 0.05)"

TEXT = "#f5f5f7"
TEXT_MUTED = "#a1a1aa"
TEXT_DIM = "#71717a"

# Acentos
VIOLET = "#a78bfa"
PINK = "#f472b6"
AMBER = "#fbbf24"
GREEN = "#34d399"
BLUE = "#60a5fa"
RED = "#f87171"
CHERRY = "#ff007f"
PEARL = "#e5e5e5"
QUANTUM = "#8a2be2"

# Gradientes de marca
GRADIENT_BRAND = f"linear-gradient(135deg, {VIOLET} 0%, {PINK} 100%)"
GRADIENT_BRAND_SOFT = f"linear-gradient(135deg, {VIOLET}22 0%, {PINK}22 100%)"
GRADIENT_GREEN = f"linear-gradient(135deg, {GREEN} 0%, {BLUE} 100%)"
GRADIENT_AMBER = f"linear-gradient(135deg, {AMBER} 0%, {PINK} 100%)"

# ── Tipografía ─────────────────────────────────────────
FONT_BODY = '"Inter", -apple-system, BlinkMacSystemFont, sans-serif'
FONT_HEAD = '"Space Grotesk", "Inter", sans-serif'
FONT_MONO = '"JetBrains Mono", "SF Mono", monospace'

# ── Radios / sombras ───────────────────────────────────
RADIUS_SM = "8px"
RADIUS = "14px"
RADIUS_LG = "20px"
RADIUS_XL = "28px"

SHADOW_CARD = "0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.2)"
SHADOW_HOVER = "0 1px 2px rgba(0,0,0,.3), 0 16px 40px rgba(167,139,250,.15)"
SHADOW_GLOW = "0 0 40px rgba(167,139,250,.25)"

# CSS raw que inyectamos globalmente (fuentes + scrollbar + body)
GLOBAL_CSS = {
    "@import": [
        "url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap')",
    ],
    "html, body": {
        "background": BG,
        "color": TEXT,
        "font_family": FONT_BODY,
        "font_feature_settings": '"cv11", "ss01"',
        "-webkit-font-smoothing": "antialiased",
    },
    "body": {
        "background": (
            f"radial-gradient(1200px 600px at 10% -10%, {VIOLET}18 0%, transparent 60%),"
            f"radial-gradient(900px 500px at 100% 10%, {PINK}15 0%, transparent 55%),"
            f"{BG}"
        ),
        "background_attachment": "fixed",
        "min_height": "100vh",
    },
    "*::-webkit-scrollbar": {"width": "8px", "height": "8px"},
    "*::-webkit-scrollbar-track": {"background": "transparent"},
    "*::-webkit-scrollbar-thumb": {
        "background": "rgba(255,255,255,.08)",
        "border_radius": "8px",
    },
    "*::-webkit-scrollbar-thumb:hover": {"background": "rgba(255,255,255,.15)"},
}

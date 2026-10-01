from __future__ import annotations

from ..config import THEME


def build_stylesheet() -> str:
    t = THEME
    return f"""
    QWidget#Root {{
        background: {t.bg};
        color: {t.text};
        font-family: "Segoe UI";
        font-size: 9pt;
    }}

    QLabel {{
        color: {t.text};
    }}

    QLineEdit {{
        background: {t.panel_alt};
        color: {t.text};
        border: 1px solid {t.border};
        border-radius: 6px;
        padding: 8px 10px;
        selection-background-color: {t.blue};
    }}

    QLineEdit:focus {{
        border: 1px solid {t.blue};
    }}

    QLineEdit:read-only {{
        color: #c0c4cd;
    }}

    QPushButton {{
        background: {t.panel_alt};
        color: {t.text};
        border: 0;
        border-radius: 6px;
        padding: 9px 12px;
        font-weight: 600;
    }}

    QPushButton:hover {{ background: {t.border_light}; }}
    QPushButton:pressed {{ background: {t.border}; }}

    QScrollBar {{ width: 0; height: 0; }}
    """

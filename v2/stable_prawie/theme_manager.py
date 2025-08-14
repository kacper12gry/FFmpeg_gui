# theme_manager.py
import urllib.parse

def get_dark_theme_qss():
    """Zwraca ostateczny, kompletny i w pełni ujednolicony arkusz stylów."""

    check_svg_raw = "<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24'><path fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round' d='M4 12l6 6L20 6'/></svg>"
    up_arrow_svg_raw = "<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24'><path fill='white' d='M7 14l5-5 5 5H7z'/></svg>"
    down_arrow_svg_raw = "<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24'><path fill='white' d='M7 10l5 5 5-5H7z'/></svg>"
    radio_check_svg_raw = "<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24'><circle cx='12' cy='12' r='8' fill='white'/></svg>"

    check_svg = urllib.parse.quote(check_svg_raw)
    up_arrow_svg = urllib.parse.quote(up_arrow_svg_raw)
    down_arrow_svg = urllib.parse.quote(down_arrow_svg_raw)
    radio_check_svg = urllib.parse.quote(radio_check_svg_raw)

    return f"""
    /* --- Globalne --- */
    QWidget {{
        background-color: #2b2b2b;
        color: #e0e0e0;
        font-family: "Segoe UI", "Arial", sans-serif;
        font-size: 10pt;
        border: none;
    }}

    /* --- POPRAWKA: Ujednolicony styl dla wszystkich przycisków --- */
    QPushButton, QDialogButtonBox QPushButton, QToolButton {{
        background-color: #E67E22;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 5px;
        font-weight: 600;
        min-height: 26px;
    }}
    QPushButton:hover, QToolButton:hover {{
        background-color: #D35400;
    }}
    QPushButton:disabled, QToolButton:disabled {{
        background-color: #555555;
        color: #888888;
    }}
    /* Ustawiamy mniejszy padding dla przycisku '?', aby nie był za szeroki */
    QToolButton {{
        padding: 6px;
    }}

    /* --- Pola wejściowe --- */
    QLineEdit, QComboBox, QSpinBox {{
        background-color: #3c3c3c;
        border: 1px solid #4f4f4f;
        border-radius: 5px;
        padding: 5px;
        min-height: 26px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 1px solid #E67E22;
    }}

    QSpinBox {{ padding-right: 20px; }}
    QSpinBox::up-button, QSpinBox::down-button {{
        subcontrol-origin: border;
        background-color: #3c3c3c;
        border: none;
        width: 18px;
    }}
    QSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: 5px; }}
    QSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: 5px; }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: #E67E22; }}
    QSpinBox::up-arrow {{ image: url('data:image/svg+xml,{up_arrow_svg}'); }}
    QSpinBox::down-arrow {{ image: url('data:image/svg+xml,{down_arrow_svg}'); }}

    /* --- CheckBox i RadioButton --- */
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px; height: 18px;
        background-color: #3c3c3c;
        border: 1px solid #4f4f4f;
    }}
    QCheckBox::indicator {{ border-radius: 4px; }}
    QRadioButton::indicator {{ border-radius: 9px; }}
    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: #E67E22; }}
    QCheckBox::indicator:checked {{
        background-color: #E67E22; border-color: #D35400;
        image: url('data:image/svg+xml,{check_svg}');
    }}
    QRadioButton::indicator:checked {{
        background-color: #E67E22; border-color: #D35400;
        image: url('data:image/svg+xml,{radio_check_svg}');
    }}

    /* --- Pozostałe style --- */
    QComboBox QAbstractItemView {{
        background-color: #3c3c3c;
        border: 1px solid #4f4f4f;
        selection-background-color: #E67E22;
        outline: none;
    }}
    QTextEdit, QListWidget {{
        background-color: #212121;
        border: 1px solid #4f4f4f;
        border-radius: 5px;
    }}
    QListWidget::item:selected {{ background-color: #E67E22; color: #ffffff; }}
    QMenuBar {{ background-color: #2b2b2b; }}
    QMenuBar::item:selected {{ background-color: #D35400; }}
    QMenu {{ background-color: #3c3c3c; border: 1px solid #4f4f4f; padding: 5px; }}
    QMenu::item:selected {{ background-color: #E67E22; }}
    QGroupBox {{
        font-weight: bold; border: 1px solid #4f4f4f;
        border-radius: 5px; margin-top: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px;
    }}
    QScrollBar:vertical {{
        background: #212121; width: 12px; margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: #555555; min-height: 20px; border-radius: 6px;
    }}
    QScrollBar::handle:vertical:hover {{ background: #E67E22; }}
    """

def get_light_theme_qss():
    return ""

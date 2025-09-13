# theme_manager.py
def get_dark_theme_qss():
    """
    Zwraca ostateczny, kompletny arkusz stylów dla ciemnego motywu,
    korzystając z zewnętrznych plików ikon.
    """
    return f"""
    /* --- Globalne --- */
    QWidget {{
        background-color: #2b2b2b; color: #e0e0e0;
        font-family: "Segoe UI", "Arial", sans-serif; font-size: 10pt;
        border: none;
    }}

    /* --- Przyciski i Pasek Narzędzi --- */
    QPushButton, QToolButton, QDialogButtonBox QPushButton {{
        background-color: #E67E22;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 5px;
        font-weight: 600;
        min-height: 26px;
        border: none;
    }}
    QPushButton:hover, QToolButton:hover {{
        background-color: #D35400;
    }}
    QPushButton:disabled, QToolButton:disabled {{
        background-color: #555555;
        color: #888888;
    }}

    QToolBar {{
        background-color: #2b2b2b;
        border: none;
        padding: 2px;
        spacing: 5px;
    }}

    QToolBar QToolButton {{
        padding: 6px 10px;
        font-weight: normal;
    }}


    /* --- Pola wejściowe --- */
    QLineEdit, QSpinBox, QComboBox {{
        background-color: #3c3c3c; border: 1px solid #4f4f4f;
        border-radius: 5px; padding: 5px; min-height: 26px;
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 1px solid #E67E22; }}
    QSpinBox {{ padding-right: 20px; }}
    QSpinBox::up-button, QSpinBox::down-button {{
        subcontrol-origin: border; background-color: #3c3c3c;
        border: none; width: 18px;
    }}
    QSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: 5px; }}
    QSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: 5px; }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background-color: #E67E22; }}
    QSpinBox::up-arrow {{ image: url(icon/arrow_up.svg); }}
    QSpinBox::down-arrow {{ image: url(icon/arrow_down.svg); }}
    QComboBox {{ padding-left: 10px; }}
    QComboBox::drop-down {{
        border: none; subcontrol-origin: padding;
        subcontrol-position: top right; width: 25px;
    }}
    QComboBox::down-arrow {{ image: url(icon/arrow_down.svg); }}
    QComboBox QAbstractItemView {{
        background-color: #3c3c3c; border: 1px solid #4f4f4f;
        selection-background-color: #E67E22;
        padding: 5px; outline: none;
    }}

    /* --- CheckBox i RadioButton --- */
    QCheckBox, QRadioButton {{
        spacing: 10px;
        background: transparent;
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px; height: 18px;
        background-color: #3c3c3c; border: 1px solid #4f4f4f;
    }}
    QCheckBox::indicator {{ border-radius: 4px; }}
    QRadioButton::indicator {{ border-radius: 9px; }}
    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: #E67E22; }}
    QCheckBox::indicator:checked {{
        background-color: #E67E22; border-color: #D35400;
        image: url(icon/check.svg);
    }}
    QRadioButton::indicator:checked {{
        background-color: #E67E22; border-color: #D35400;
    }}
    QRadioButton::indicator:disabled, QCheckBox::indicator:disabled {{
        background-color: #555555;
    }}

    /* --- POPRAWIONE: Listy i Pola Tekstowe --- */
    QTextEdit, QListWidget {{
        background-color: #212121;
        border: 1px solid #4f4f4f;
        border-radius: 5px;
        padding: 5px;
        outline: 0px; /* Całkowite wyłączenie systemowego obramowania */
        font-family: "Consolas", "Monaco", "monospace"; /* Czcionka o stałej szerokości dla logów */
    }}
    /* --- NOWE: Obejście dla białej poświaty --- */
    QTextEdit:focus, QListWidget:focus {{
        border: 1px solid #4f4f4f; /* Pozostawiamy standardowe obramowanie, bez zmiany koloru */
    }}
    QListWidget::item {{
        padding: 5px;
        border-radius: 4px;
    }}
    QListWidget::item:hover {{
        background-color: #3c3c3c;
    }}
    QListWidget::item:selected {{
        background-color: #E67E22;
        color: #ffffff;
    }}

    /* --- Zakładki (Tabs) --- */
    QTabWidget::pane {{
        border: 1px solid #4f4f4f; border-radius: 5px;
        border-top-left-radius: 0px; background: #2b2b2b;
        margin-top: -1px;
    }}
    QTabBar::tab {{
        background: #3c3c3c; border: 1px solid #4f4f4f;
        border-bottom: none; padding: 8px 16px;
        border-top-left-radius: 5px; border-top-right-radius: 5px;
        font-weight: bold; color: #aaaaaa;
    }}
    QTabBar::tab:hover {{ background: #4a4a4a; }}
    QTabBar::tab:selected {{
        background: #2b2b2b; color: #e0e0e0; border-color: #4f4f4f;
    }}

    /* --- Suwak (Splitter) --- */
    QSplitter::handle:vertical {{
        image: url(icon/splitter_handle_horizontal.svg);
        height: 10px;
    }}
    QSplitter::handle:horizontal {{
        image: url(icon/splitter_handle.svg);
        width: 10px;
    }}

    /* --- Menu --- */
    QMenuBar {{
        background-color: #2b2b2b; spacing: 5px;
    }}
    QMenuBar::item {{
        background: transparent; padding: 4px 8px;
    }}
    QMenuBar::item:selected {{
        background: #3c3c3c; border-radius: 4px;
    }}
    QMenuBar::item:pressed {{
        background: #E67E22; color: #ffffff;
    }}
    QMenu {{
        background-color: #2b2b2b;
        border: 1px solid #555555;
        padding: 5px;
        border-radius: 5px;
    }}
    QMenu::item {{
        padding: 5px 25px 5px 15px;
    }}
    QMenu::item:selected {{
        background-color: #E67E22;
        border-radius: 4px;
    }}
    QMenu::separator {{
        height: 1px; background: #555555; margin: 5px 0px;
    }}
    QMenu::indicator {{
        width: 13px; height: 13px;
        padding-left: 5px;
    }}
    QMenu::indicator:non-exclusive:checked {{
        image: url(icon/check.svg);
    }}
    QMenu::indicator:exclusive:checked {{
        image: url(icon/radio.svg);
    }}
        /* --- Pasek Postępu (ProgressBar) --- */
    QProgressBar {{
        border: 1px solid #4f4f4f;
        border-radius: 5px;
        background-color: #2b2b2b;
        text-align: center;
        color: #e0e0e0; /* Kolor tekstu procentowego height: 6px; */
    }}

    QProgressBar::chunk {{
        background-color: #E67E22; /* Kolor paska postępu */
        border-radius: 4px;
        margin: 1px; /* Daje mały odstęp między paskiem a ramką */
    }}


    /* --- Pozostałe --- */
    QGroupBox {{
        font-weight: bold; border: 1px solid #4f4f4f;
        border-radius: 5px; margin-top: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; subcontrol-position: top center;
        padding: 0 5px;
    }}
    /* --- Paski przewijania (ScrollBars) --- */
    QScrollBar:vertical, QScrollBar:horizontal {{
        background: #212121;
        width: 12px; height: 12px;
        margin: 0; border-radius: 6px;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: #555555;
        min-height: 20px; min-width: 20px;
        border-radius: 6px;
    }}
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
        background: #E67E22;
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0px; width: 0px;
    }}
    """

def get_light_theme_qss():
    """Zwraca pusty arkusz stylów dla motywu jasnego/systemowego."""
    return ""

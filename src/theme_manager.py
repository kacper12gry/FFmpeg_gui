# theme_manager.py
def get_dark_theme_qss():
    """
    Zwraca ostateczny, kompletny arkusz stylów dla ciemnego motywu,
    korzystając z zewnętrznych plików ikon.
    """
    return """
    /* --- Globalne --- */
    QWidget {
        background-color: #2b2b2b;
        color: #e0e0e0;
        font-family: "Segoe UI", "Arial", sans-serif;
        font-size: 10pt;
        border: none;
    }

    /* --- Przyciski i Pasek Narzędzi --- */
    QPushButton, QToolButton, QDialogButtonBox QPushButton {
        background-color: #E67E22;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 5px;
        font-weight: 600;
        min-height: 26px;
        border: none;
    }
    QPushButton:hover, QToolButton:hover {
        background-color: #D35400;
    }
    QPushButton:disabled, QToolButton:disabled {
        background-color: #555555;
        color: #888888
    }

    /* Specjalny styl dla mniejszych przycisków */
    QPushButton#smallButton {
        padding-top: 0px;
        padding-bottom: 0px;
        margin-top: 0px;
        margin-bottom: 0px;
        min-height: 0px;
    }

    QToolBar {
        background-color: #2b2b2b;
        border: none;
        padding: 2px;
        spacing: 5px;
    }

    QToolBar QToolButton {
        padding: 6px 10px;
        font-weight: normal;
    }


    /* --- Pola wejściowe --- */
    QLineEdit, QSpinBox, QComboBox {
        background-color: #3c3c3c;
        border: 1px solid #4f4f4f;
        border-radius: 5px;
        padding: 5px;
        min-height: 26px;
        color: #e0e0e0; /* Dodano kolor tekstu dla stanu normalnego */
    }
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
        border: 1px solid #E67E22;
    }
    /* NOWE: Style dla wyłączonych pól tekstowych */
    QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
        background-color: #444444;
        color: #888888;
        border: 1px solid #4a4a4a;
    }

    QSpinBox { padding-right: 20px; }
    QSpinBox::up-button, QSpinBox::down-button {
        subcontrol-origin: border;
        background-color: #3c3c3c;
        border: none;
        width: 18px;
    }
    QSpinBox::up-button { subcontrol-position: top right; border-top-right-radius: 5px; }
    QSpinBox::down-button { subcontrol-position: bottom right; border-bottom-right-radius: 5px; }
    QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #E67E22; }
    QSpinBox::up-arrow { image: url(icon/arrow_up.svg); }
    QSpinBox::down-arrow { image: url(icon/arrow_down.svg); }

    QComboBox { padding-left: 10px; }
    QComboBox::drop-down {
        border: none;
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 25px;
    }
    QComboBox::down-arrow { image: url(icon/arrow_down.svg); }
    QComboBox QAbstractItemView {
        background-color: #3c3c3c;
        border: 1px solid #4f4f4f;
        selection-background-color: #E67E22;
        padding: 5px;
        outline: none;
        color: #e0e0e0;
    }
    QComboBox QAbstractItemView::item {
        padding: 5px 10px;
    }
    QComboBox QAbstractItemView::item:hover {
        background-color: #4a4a4a;
    }

    /* --- CheckBox i RadioButton --- */
    QCheckBox, QRadioButton {
        spacing: 10px;
        background: transparent;
        color: #e0e0e0; /* Dodano kolor tekstu dla stanu normalnego */
    }
    /* NOWE: Style dla wyłączonego tekstu checkboxa/radio */
    QCheckBox:disabled, QRadioButton:disabled {
        color: #888888;
    }

    QCheckBox::indicator, QRadioButton::indicator {
        width: 18px;
        height: 18px;
        background-color: #3c3c3c;
        border: 1px solid #4f4f4f;
    }
    QCheckBox::indicator { border-radius: 4px; }
    QRadioButton::indicator { border-radius: 9px; }
    QCheckBox::indicator:hover, QRadioButton::indicator:hover { border-color: #E67E22; }

    QCheckBox::indicator:checked {
        background-color: #E67E22;
        border-color: #D35400;
        image: url(icon/check.svg);
    }
    QRadioButton::indicator:checked {
        background-color: #E67E22;
        border-color: #D35400;
    }

    QRadioButton::indicator:disabled, QCheckBox::indicator:disabled {
        background-color: #555555;
        border-color: #666666;
    }

    /* --- Listy i Pola Tekstowe --- */
    QTextEdit, QListWidget {
        background-color: #212121;
        border: 1px solid #4f4f4f;
        border-radius: 5px;
        padding: 5px;
        outline: 0px;
        font-family: "Consolas", "Monaco", "monospace";
        color: #e0e0e0; /* Dodano kolor tekstu dla stanu normalnego */
    }
    /* NOWE: Style dla wyłączonych list i pól tekstowych */
    QTextEdit:disabled, QListWidget:disabled {
        background-color: #444444;
        color: #888888;
    }

    QTextEdit:focus, QListWidget:focus {
        border: 1px solid #4f4f4f;
    }

    QListWidget::item {
        padding: 5px;
        border-radius: 4px;
    }
    QListWidget::item:hover {
        background-color: #3c3c3c;
    }
    QListWidget::item:selected {
        background-color: #E67E22;
        color: #ffffff;
    }

    /* --- Zakładki (Tabs) --- */
    QTabWidget::pane {
        border: 1px solid #4f4f4f;
        border-radius: 5px;
        border-top-left-radius: 0px;
        background: #2b2b2b;
        margin-top: -1px;
    }
    QTabBar::tab {
        background: #3c3c3c;
        border: 1px solid #4f4f4f;
        border-bottom: none;
        padding: 8px 16px;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
        font-weight: bold;
        color: #aaaaaa;
    }
    QTabBar::tab:hover { background: #4a4a4a; }
    QTabBar::tab:selected {
        background: #2b2b2b;
        color: #e0e0e0;
        border-color: #4f4f4f;
    }

    /* --- Suwak (Splitter) --- */
    QSplitter::handle:vertical {
        image: url(icon/splitter_handle_horizontal.svg);
        height: 10px;
    }
    QSplitter::handle:horizontal {
        image: url(icon/splitter_handle.svg);
        width: 10px;
    }

    /* --- Menu --- */
    QMenuBar {
        background-color: #2b2b2b;
        spacing: 5px;
    }
    QMenuBar::item {
        background: transparent;
        padding: 4px 8px;
    }
    QMenuBar::item:selected {
        background: #3c3c3c;
        border-radius: 4px;
    }
    QMenuBar::item:pressed {
        background: #E67E22;
        color: #ffffff;
    }

    QMenu {
        background-color: #2b2b2b;
        border: 1px solid #555555;
        padding: 5px;
        border-radius: 5px;
    }
    QMenu::item {
        padding: 5px 25px 5px 15px;
    }
    QMenu::item:selected {
        background-color: #E67E22;
        border-radius: 4px;
    }
    QMenu::separator {
        height: 1px;
        background: #555555;
        margin: 5px 0px;
    }
    QMenu::indicator {
        width: 13px;
        height: 13px;
        padding-left: 5px;
    }
    QMenu::indicator:non-exclusive:checked {
        image: url(icon/check.svg);
    }
    QMenu::indicator:exclusive:checked {
        image: url(icon/radio.svg);
    }

    /* --- Pasek Postępu (ProgressBar) --- */
    QProgressBar {
        border: 1px solid #4f4f4f;
        border-radius: 5px;
        background-color: #2b2b2b;
        text-align: center;
        color: #e0e0e0;
    }
    QProgressBar::chunk {
        background-color: #E67E22;
        border-radius: 4px;
        margin: 1px;
    }

    /* --- Pozostałe --- */
    QGroupBox {
        font-weight: bold;
        border: 1px solid #4f4f4f;
        border-radius: 5px;
        margin-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 5px;
    }

    /* --- Paski przewijania (ScrollBars) --- */
    QScrollBar:vertical {
        width: 8px;
    }
    QScrollBar:horizontal {
        height: 8px;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
        background: #555;
        border-radius: 4px;
        min-height: 25px;
        min-width: 25px;
    }
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
        background: #E67E22;
    }
    QScrollBar::add-line, QScrollBar::sub-line {
        height: 0px;
        width: 0px;
        background: none;
    }
    """

def get_light_theme_qss():
    """Zwraca pusty arkusz stylów dla motywu jasnego/systemowego."""
    return ""

def get_professional_light_theme_qss():
    """Zwraca kompletny arkusz stylów dla profesjonalnego motywu jasnego."""
    return """
    /* --- Globalne --- */
    QWidget {
        background-color: #F5F5F5;
        color: #111111;
        font-family: "Segoe UI", "Arial", sans-serif;
        font-size: 10pt;
        border: none;
    }

    /* --- Przyciski i Pasek Narzędzi --- */
    QPushButton, QToolButton, QDialogButtonBox QPushButton {
        background-color: #0078D4;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 4px;
        font-weight: 600;
        min-height: 26px;
        border: 1px solid #005A9E;
    }
    QPushButton:hover, QToolButton:hover {
        background-color: #005A9E;
    }
    QPushButton:disabled, QToolButton:disabled {
        background-color: #E0E0E0;
        color: #A0A0A0;
        border: 1px solid #CCCCCC;
    }
    /* Specjalny styl dla mniejszych przycisków */
    QPushButton#smallButton {
        padding-top: 0px;
        padding-bottom: 0px;
        margin-top: 0px;
        margin-bottom: 0px;
        min-height: 0px;
    }
    QToolBar {
        background-color: #F5F5F5;
        border-bottom: 1px solid #E0E0E0;
        padding: 2px;
        spacing: 5px;
    }

    /* --- Pola wejściowe --- */
    QLineEdit, QSpinBox, QComboBox, QTextEdit, QListWidget {
        background-color: #FFFFFF;
        color: #111111;
        border: 1px solid #C0C0C0;
        border-radius: 4px;
        padding: 5px;
        min-height: 26px;
    }
    QTextEdit, QListWidget {
        outline: none; /* Usuwa domyślną ramkę fokusu */
    }
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
        border: 1px solid #0078D4; /* Pozostawia ramkę fokusu dla pól edycji */
    }
    QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled, QTextEdit:disabled, QListWidget:disabled {
        background-color: #F0F0F0;
        color: #A0A0A0;
        border: 1px solid #E0E0E0;
    }

    QSpinBox::up-button, QSpinBox::down-button { background-color: #F5F5F5; border-left: 1px solid #E0E0E0; }
    QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #E0E0E0; }
    QSpinBox::up-arrow { image: url(icon/arrow_up_dark.svg); }
    QSpinBox::down-arrow { image: url(icon/arrow_down_dark.svg); }

    QComboBox::drop-down { border: none; }
    QComboBox::down-arrow { image: url(icon/arrow_down_dark.svg); }
    QComboBox QAbstractItemView {
        background-color: #FFFFFF;
        border: 1px solid #C0C0C0;
        selection-background-color: #0078D4;
        selection-color: #FFFFFF;
        padding: 4px;
        outline: none;
    }
    QComboBox QAbstractItemView::item {
        padding: 5px 10px;
        color: #111111;
    }
    QComboBox QAbstractItemView::item:hover {
        background-color: #E3F2FD;
    }

    /* --- CheckBox i RadioButton --- */
    QCheckBox, QRadioButton { spacing: 8px; background: transparent; }
    QCheckBox:disabled, QRadioButton:disabled { color: #A0A0A0; }
    QCheckBox::indicator, QRadioButton::indicator { width: 18px; height: 18px; background-color: #FFFFFF; border: 1px solid #C0C0C0; border-radius: 4px; }
    QRadioButton::indicator { border-radius: 9px; }
    QCheckBox::indicator:hover, QRadioButton::indicator:hover { border-color: #0078D4; }
    QCheckBox::indicator:checked { background-color: #0078D4; border-color: #005A9E; image: url(icon/check.svg); }
    QRadioButton::indicator:checked { background-color: qradialgradient(cx:0.5, cy:0.5, radius: 0.4, fx:0.5, fy:0.5, stop:0 #0078D4, stop:1 #0078D4); border: 1px solid #0078D4; }

    /* --- Listy i Pola Tekstowe --- */
    QListWidget::item { padding: 5px; border-radius: 4px; }
    QListWidget::item:hover { background-color: #E3F2FD; }
    QListWidget::item:selected { background-color: #0078D4; color: #FFFFFF; }

    /* --- Zakładki (Tabs) --- */
    QTabWidget::pane {
        border: 1px solid #E0E0E0;
        top: -1px; /* Przesuń panel w górę, aby nachodził na pasek zakładek */
    }
    QTabBar::tab {
        background: #E9E9E9;
        border: 1px solid #E0E0E0;
        padding: 8px 16px;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
        color: #555555;
        font-weight: bold;
    }
    QTabBar::tab:hover {
        background: #F0F0F0;
    }
    QTabBar::tab:selected {
        background: #F5F5F5; /* Kolor tła okna */
        color: #111111;
        border-bottom-color: #F5F5F5; /* Niewidoczna dolna krawędź */
    }
    QTabBar::tab:!selected {
        margin-top: 2px; /* Lekko obniż nieaktywne zakładki */
    }

    /* --- Suwak (Splitter) --- */
    QSplitter::handle:vertical {
        image: url(icon/splitter_handle_horizontal.svg);
        height: 10px;
    }
    QSplitter::handle:horizontal {
        image: url(icon/splitter_handle.svg);
        width: 10px;
    }

    /* --- Menu --- */
    QMenuBar { background-color: #F5F5F5; }
    QMenuBar::item { background: transparent; padding: 4px 8px; }
    QMenuBar::item:selected { background: #E0E0E0; border-radius: 4px; }
    QMenu { background-color: #FFFFFF; border: 1px solid #C0C0C0; padding: 5px; }
    QMenu::item { padding: 5px 25px 5px 15px; }
    QMenu::item:selected { background-color: #0078D4; color: #FFFFFF; border-radius: 4px; }
    QMenu::separator { height: 1px; background: #E0E0E0; margin: 5px 0px; }
    QMenu::indicator { width: 13px; height: 13px; padding-left: 5px; }
    QMenu::indicator:non-exclusive:checked { image: url(icon/check_dark.svg); }
    QMenu::indicator:exclusive:checked { image: url(icon/radio_dark.svg); }

    /* --- Pasek Postępu (ProgressBar) --- */
    QProgressBar { border: 1px solid #C0C0C0; border-radius: 4px; background-color: #FFFFFF; text-align: center; color: #111111; }
    QProgressBar::chunk { background-color: #0078D4; border-radius: 3px; margin: 1px; }

    /* --- Pozostałe --- */
    QGroupBox {
        font-weight: bold;
        border: 1px solid #E0E0E0;
        border-radius: 5px;
        margin-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 5px;
        background-color: #F5F5F5; /* Tło tytułu takie jak tło okna */
    }
    QToolTip { padding: 5px; background-color: #2b2b2b; color: white; border: 1px solid #4f4f4f; }
    QStatusBar { background-color: #EAEAEA; border-top: 1px solid #E0E0E0; }
    QHeaderView::section {
        background-color: #F0F0F0;
        padding: 6px;
        border: none;
        border-bottom: 1px solid #D0D0D0;
        font-weight: bold;
    }

    /* --- Paski przewijania (ScrollBars) --- */
    QScrollBar:vertical {
        width: 8px;
    }
    QScrollBar:horizontal {
        height: 8px;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
        background: #C0C0C0;
        border-radius: 4px;
        min-height: 25px;
        min-width: 25px;
    }
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
        background: #0078D4;
    }
    QScrollBar::add-line, QScrollBar::sub-line {
        height: 0px;
        width: 0px;
        background: none;
    }
    """

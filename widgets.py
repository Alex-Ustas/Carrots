from typing import List, Optional
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QComboBox, QSpinBox, QLineEdit, QGridLayout, QFrame
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtCore import QSize, pyqtSignal

TEXT_COLOR = '#203764'  # тёмно-синий


class Label(QLabel):
    def __init__(self, text: str, fixed_width=0, fixed_height=30):
        super().__init__(text)
        self.setStyleSheet(f'color: {TEXT_COLOR}; font-size: 16px; font-weight: bold')
        if fixed_width:
            self.setFixedWidth(fixed_width)
        if fixed_height:
            self.setFixedHeight(fixed_height)


class EditBox(QLineEdit):
    def __init__(self, text='', fixed_width=0, fixed_height=30, date_mask=False):
        super().__init__(text)
        self.setStyleSheet(f'color: {TEXT_COLOR}; font-size: 16px; font-weight: bold')
        if fixed_width:
            self.setFixedWidth(fixed_width)
        if fixed_height:
            self.setFixedHeight(fixed_height)
        if date_mask:
            self.setInputMask('99.99.99;_')


class Button(QPushButton):
    def __init__(self, text: str, fixed_width=0, fixed_height=40, icon_size=16):
        super().__init__()
        self.setText(text)
        self.setStyleSheet(f"""
            QPushButton {{font-size: 16px; font-weight: bold; color: {TEXT_COLOR}; border: 2px groove #c0c0c0; border-radius: 6px;
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 #f0f0f0, stop: 1 #d0d0d0)}}
            QPushButton::disabled {{background-color: #D9D9D9; color: gray; font-weight: bold}}
            QPushButton::hover {{background-color: {TEXT_COLOR}; color: white; font-weight: bold}}
            """)
        self.setIconSize(QSize(icon_size, icon_size))
        if fixed_width:
            self.setFixedWidth(fixed_width)
        if fixed_height:
            self.setFixedHeight(fixed_height)


class CardButton(QPushButton):
    def __init__(self, text: str):
        super().__init__()
        self.setText(text)
        self.setStyleSheet(f"""
            font-size: 14px; font-weight: bold; color: {TEXT_COLOR}; border: 1px solid black; border-radius: 6px;
            background-color: white;
            """)
        self.setFixedSize(40, 40)


class ComboList(QComboBox):
    def __init__(self, fixed_width=0, fixed_height=30, editable=False, date_mask=False):
        super().__init__()
        self.setStyleSheet(f'color: {TEXT_COLOR}; font-size: 16px')
        self.setMaxVisibleItems(10)
        self.setEditable(editable)
        if fixed_width:
            self.setFixedWidth(fixed_width)
        if fixed_height:
            self.setFixedHeight(fixed_height)
        if date_mask:
            self.lineEdit().setInputMask('99.99.99;_')


class EditSpin(QSpinBox):
    def __init__(self, fixed_width=0, fixed_height=30, maximum=1000, step=5):
        super().__init__()
        self.setStyleSheet(f'color: {TEXT_COLOR}; font-size: 16px; font-weight: bold')
        if fixed_width:
            self.setFixedWidth(fixed_width)
        if fixed_height:
            self.setFixedHeight(fixed_height)
        if maximum:
            self.setMaximum(maximum)
        if step:
            self.setSingleStep(step)


class CardWidget(QFrame):
    cell_clicked = pyqtSignal(int)

    def __init__(self, rows: int, cols: int, active: int):
        super().__init__()
        self.active = active
        self.total = rows * cols
        self.setStyleSheet("background-color: white; border: 1px solid black;")

        self._bg_colors: List[Optional[QColor]] = [None] * self.total
        self._borders: List[Optional[str]] = [None] * self.total

        layout = QGridLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        self.buttons: List[CardButton] = []
        for i in range(self.total):
            btn = CardButton(str(i + 1))
            btn.clicked.connect(lambda _, idx=i: self.cell_clicked.emit(idx))  # type: ignore
            self.buttons.append(btn)
            r, c = divmod(i, cols)
            layout.addWidget(btn, r, c)
            if i >= active:
                btn.setVisible(False)

    def _build_style(self, idx: int) -> str:
        bg = self._bg_colors[idx]
        border = self._borders[idx]
        bg_str = bg.name() if bg else "white"
        border_str = f"4px solid {border}" if border else "1px solid black"
        return (f"font-size: 14px; font-weight: bold; color: {TEXT_COLOR}; "
                f"border: {border_str}; border-radius: 6px; "
                f"background-color: {bg_str};")

    def set_cell_color(self, idx: int, color: Optional[QColor]):
        if idx < 0 or idx >= self.active:
            return
        self._bg_colors[idx] = color
        self.buttons[idx].setStyleSheet(self._build_style(idx))

    def set_cell_border(self, idx: int, border_color: Optional[str]):
        if idx < 0 or idx >= self.active:
            return
        self._borders[idx] = border_color
        self.buttons[idx].setStyleSheet(self._build_style(idx))

    def clear_all_borders(self):
        for i in range(self.active):
            self._borders[i] = None
            self.buttons[i].setStyleSheet(self._build_style(i))


class Window(QWidget):
    def __init__(self, text: str, width=300, height=300):
        super().__init__()
        self.setMinimumSize(width, height)
        self.setWindowTitle(text)
        self.setWindowIcon(QIcon('images/carrots.png'))

    def delete_widgets(self, layout):
        while layout.count() > 0:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

            child_layout = item.layout()
            if child_layout is not None:
                self.delete_widgets(child_layout)
                child_layout.deleteLater()

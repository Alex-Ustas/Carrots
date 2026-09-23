# TODO:

import sys, json, random, os, re
from datetime import datetime as dt
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, asdict, field
from copy import deepcopy
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, date2num
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QVBoxLayout, QMessageBox, QFrame, QGridLayout, QTableWidget,
                             QWidget, QLabel, QPushButton, QComboBox, QRadioButton, QScrollArea, QSpinBox,
                             QHeaderView, QTableWidgetItem, QInputDialog, QListWidget)
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtCore import QSize, pyqtSignal, Qt

VERSION = '1.12 (2026.09)'
DATA_DIR = "data"
TICKETS_FILE = os.path.join(DATA_DIR, "tickets.json")
RESULTS_FILE = os.path.join(DATA_DIR, "results.json")
WINNINGS_FILE = os.path.join(DATA_DIR, "win_sets.json")

CARD1_SIZE = 35
CARD2_SIZE = 54
WINNING_VARIANTS = [
    (2, 0), (3, 0), (4, 0), (1, 1), (0, 1), (2, 1), (3, 1),
    (5, 0), (4, 1), (6, 0), (5, 1), (6, 1), (7, 0), (7, 1)
]

COLORS = [
    QColor("#9ac87d"),  # 1 — светло-зелёный
    QColor("#00b0f0"),  # 2 — голубой #dcfdfd
    QColor("yellow"),  # 3 — светло-жёлтый #fff9c4
    QColor("#a0a0a0"),  # 4 — светло-серый
    QColor("#ffaaaa"),  # 5 — светло-красный
]
RESULT_COLOR = QColor("#FFC000")


def choose_plural(amount: int, declensions: Tuple[str, str, str]) -> str:
    """Show the number of subjects in the corresponding declension"""
    if amount % 10 == 1 and amount % 100 != 11:
        return f'{amount} {declensions[0]}'
    elif (amount % 10 == 2 and amount % 100 != 12 or
          amount % 10 == 3 and amount % 100 != 13 or
          amount % 10 == 4 and amount % 100 != 14):
        return f'{amount} {declensions[1]}'
    else:
        return f'{amount} {declensions[2]}'


def is_valid_date(date_str: str) -> bool:
    """Проверяет, что строка в формате dd.mm.yy и является реальной датой."""
    if not date_str:
        return False
    try:
        dt.strptime(date_str, "%d.%m.%y")
        return True
    except ValueError:
        return False


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_all_tickets() -> Dict[str, 'TicketSets']:
    ensure_data_dir()
    if not os.path.exists(TICKETS_FILE):
        return {}
    try:
        with open(TICKETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {d["date"]: TicketSets.from_dict(d) for d in data}
    except Exception:
        return {}


def save_all_tickets(data: Dict[str, 'TicketSets']):
    ensure_data_dir()
    serialized = [d.to_dict() for d in data.values()]
    with open(TICKETS_FILE, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)


def load_all_results() -> Dict[str, 'Result']:
    ensure_data_dir()
    if not os.path.exists(RESULTS_FILE):
        return {}
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {r["date"]: Result.from_dict(r) for r in data}
    except Exception:
        return {}


def save_all_results(data: Dict[str, 'Result']):
    ensure_data_dir()
    serialized = [r.to_dict() for r in data.values()]
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)


def load_all_winnings() -> Dict[str, 'Winning']:
    ensure_data_dir()
    if not os.path.exists(WINNINGS_FILE):
        return {}
    try:
        with open(WINNINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {w["name"]: Winning.from_dict(w) for w in data}
    except Exception:
        return {}


def save_all_winnings(data: Dict[str, "Winning"]):
    ensure_data_dir()
    serialized = [w.to_dict() for w in data.values()]
    with open(WINNINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)


@dataclass
class Ticket:
    ticket: int
    first_card_selected: List[int]  # индексы 0..34 (всего 35)
    second_card_selected: Optional[int]  # индекс 0..53 (всего 54)

    def is_valid(self) -> bool:
        """Валиден, если выбрано ровно 7 ячеек в первой карточке и 1 во второй"""
        return len(self.first_card_selected) == 7 and self.second_card_selected is not None


@dataclass
class TicketSets:
    date: str  # dd.mm.yy
    cost: int
    win_set: str
    sets: List[List[Ticket]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "TicketSets":
        sets = []
        for s in d.get("sets", []):
            sets.append([Ticket(**t) for t in s])
        return cls(date=d["date"], cost=d['cost'], win_set=d['win_set'], sets=sets)

    def to_dict(self) -> dict:
        sets_serialized = []
        for s in self.sets:
            sets_serialized.append([asdict(t) for t in s])
        return {"date": self.date, 'cost': self.cost, 'win_set': self.win_set, "sets": sets_serialized}

    def get_current_tickets(self, set_index: int) -> List[Ticket]:
        if 0 <= set_index < len(self.sets):
            return self.sets[set_index]
        return []

    def add_empty_set(self):
        self.sets.append([])

    def remove_set(self, index: int):
        if 0 <= index < len(self.sets):
            del self.sets[index]

    @staticmethod
    def is_set_full(tickets: List[Ticket]) -> bool:
        """Набор полон, если в нём ровно 5 валидных билетов"""
        if len(tickets) != 5:
            return False
        return all(t.is_valid() for t in tickets)

    def is_valid(self) -> bool:
        """
        Валидация по правилам:
        1. Дата в формате dd.mm.yy.
        2. Стоимость > 0
        3. Есть хотя бы один набор.
        4. Все наборы кроме последнего — полные (5 валидных билетов).
        5. В последнем наборе есть хотя бы один валидный билет.
        """
        if not is_valid_date(self.date):
            return False
        if not self.cost:
            return False
        if not self.sets:
            return False
        for s in self.sets[:-1]:
            if not self.is_set_full(s):
                return False
        if not any(t.is_valid() for t in self.sets[-1]):
            return False

        return True


@dataclass
class Result:
    date: str
    win_set: str
    first_card_selected: List[int]
    second_card_selected: Optional[int]

    @classmethod
    def from_dict(cls, d: dict) -> "Result":
        return cls(date=d["date"],
                   win_set=d['win_set'],
                   first_card_selected=d.get("first_card_selected", []),
                   second_card_selected=d.get("second_card_selected"))

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "win_set": self.win_set,
            "first_card_selected": self.first_card_selected,
            "second_card_selected": self.second_card_selected
        }

    def is_valid(self) -> bool:
        if (is_valid_date(self.date) and
                self.win_set and
                self.second_card_selected and
                len(self.first_card_selected) == 7):
            return True
        return False

    def calculate_winnings_for_tickets(self, winning_scheme: 'Winning', tickets_source: TicketSets) \
            -> Tuple[int, int, int]:
        """
        Рассчитывает суммарный выигрыш (в 'м.' и 'б.') и затраты
        для всех валидных билетов из tickets по текущему результату.
        Возвращает: (won_m, won_b, spent).
        """
        valid_count = 0
        won_m = 0
        won_b = 0

        for ticket_set in tickets_source.sets:
            for ticket in ticket_set:
                if not ticket.is_valid():
                    continue

                valid_count += 1

                x = len(set(ticket.first_card_selected) & set(self.first_card_selected))
                y = (
                    1
                    if (ticket.second_card_selected is not None
                        and ticket.second_card_selected == self.second_card_selected)
                    else 0
                )

                prize = winning_scheme.sets.get((x, y))
                if prize:
                    amount, kind = prize
                    if kind == 'м.':
                        won_m += amount
                    elif kind == 'б.':
                        won_b += amount

        spent = valid_count * tickets_source.cost
        return won_m, won_b, spent


@dataclass
class Winning:
    name: str
    sets: Dict[Tuple[int, int], list]

    @classmethod
    def from_dict(cls, d: dict) -> "Winning":
        raw_sets = d.get("sets", {})
        parsed_sets = {}
        for k, v in raw_sets.items():
            parsed_sets[cls._parse_key(k)] = v
        return cls(name=d["name"], sets=parsed_sets)

    def to_dict(self) -> dict:
        raw_sets = {}
        for k, v in self.sets.items():
            raw_sets[self._format_key(k)] = v
        return {"name": self.name, "sets": raw_sets}

    @staticmethod
    def _parse_key(key: str) -> Tuple[int, int]:
        parts = key.split("_")
        return int(parts[0]), int(parts[1])

    @staticmethod
    def _format_key(key: Tuple[int, int]) -> str:
        return f"{key[0]}_{key[1]}"


class Label(QLabel):
    def __init__(self, text: str, fixed_width=0, fixed_height=30):
        super().__init__(text)
        self.setStyleSheet('color: #203764; font-size: 16px; font-weight: bold')
        if fixed_width:
            self.setFixedWidth(fixed_width)
        if fixed_height:
            self.setFixedHeight(fixed_height)


class Button(QPushButton):
    def __init__(self, text: str, fixed_width=0, fixed_height=40, icon_size=16):
        super().__init__()
        self.setText(text)
        self.setStyleSheet("""
            QPushButton {font-size: 16px; font-weight: bold; color: #203764; border: 2px groove #c0c0c0; border-radius: 6px;
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 #f0f0f0, stop: 1 #d0d0d0)}
            QPushButton::disabled {background-color: #D9D9D9; color: gray; font-weight: bold}
            QPushButton::hover {background-color: #203764; color: white; font-weight: bold}
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
        self.setStyleSheet("""
            font-size: 14px; font-weight: bold; color: #203764; border: 1px solid black; border-radius: 6px;
            background-color: white;
            """)
        self.setFixedSize(40, 40)


class ComboList(QComboBox):
    def __init__(self, fixed_width=0, fixed_height=30, editable=False, date_mask=False):
        super().__init__()
        self.setStyleSheet('color: #203764; font-size: 16px')
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
        self.setStyleSheet('color: #203764; font-size: 16px; font-weight: bold')
        if fixed_width:
            self.setFixedWidth(fixed_width)
        if fixed_height:
            self.setFixedHeight(fixed_height)
        if maximum:
            self.setMaximum(maximum)
        if step:
            self.setSingleStep(step)


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


class WelcomeWindow(Window):
    def __init__(self):
        super().__init__('Carrots', height=270)
        self._init_ui()

    def _init_ui(self):
        button_input = Button('Билеты', fixed_height=50)
        button_input.clicked.connect(self.open_input_data_window)
        button_results = Button('Результаты', fixed_height=50)
        button_results.clicked.connect(self.open_results_window)
        button_winning = Button('Схемы призов', fixed_height=50)
        button_winning.clicked.connect(self.open_winning_window)
        button_stat = Button('Статистика', fixed_height=50)
        button_stat.clicked.connect(self.open_stat_window)
        button_about = Button('О программе', fixed_height=50)
        button_about.clicked.connect(self.on_click_about)

        main_v_layout = QVBoxLayout()
        main_v_layout.addWidget(button_input)
        main_v_layout.addWidget(button_results)
        main_v_layout.addWidget(button_winning)
        main_v_layout.addWidget(button_stat)
        main_v_layout.addWidget(button_about)
        self.setLayout(main_v_layout)

    def open_input_data_window(self):
        self.window = TicketWindow()
        self.window.show()
        self.close()

    def open_results_window(self):
        self.window = ResultWindow('')
        self.window.show()
        self.close()

    def open_winning_window(self):
        self.window = WinningWindow()
        self.window.show()
        self.close()

    def open_stat_window(self):
        self.window = StatisticWindow()
        self.window.show()
        self.close()

    def on_click_about(self):
        name = [1060, 1072, 1076, 1077, 1080, 1095, 1077, 1074, 32, 1040, 1083, 1077, 1082, 1089, 1072, 1085, 1076,
                1088]
        fio = ''.join([chr(c) for c in name])
        html_text = f"""
        <h3><p><b>Автор:</b> {fio}</p></h3>
        <p><b>Telegram:</b> @AlexUstas0</p>
        <p><b>email:</b> alex.ustas@internet.ru</p>
        <p><b>Версия:</b> {VERSION}</p>
        """
        QMessageBox.information(self, 'О программе', html_text)


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
        return (f"font-size: 14px; font-weight: bold; color: #203764; "
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


class TicketWindow(Window):
    def __init__(self):
        super().__init__('Билеты', width=800, height=600)
        self.tickets_data: Dict[str, TicketSets] = load_all_tickets()
        self.winning_data: Dict[str, Winning] = load_all_winnings()
        self.current_date: Optional[str] = None
        self.selected_ticket_index = 0
        self.current_set_index = 0
        self.first_time = True
        self.original_data = None

        self.results_data: Dict[str, Result] = load_all_results()
        self.excluded_nums = self.calc_top_nums()

        # Рабочее состояние: 0 = пусто, 1..5 = цвет (номер билета)
        self.first_card: List[int] = [0] * CARD1_SIZE
        self.second_card: List[int] = [0] * CARD2_SIZE

        self._init_ui()
        self._refresh_dates()

    def _init_ui(self):
        main_layout = QHBoxLayout()

        # === Левая панель ===
        left = QWidget()
        left_layout = QVBoxLayout()
        left.setLayout(left_layout)

        # 1. Дата
        date_row = QHBoxLayout()
        self.date_combo = ComboList(fixed_width=100, editable=True, date_mask=True)
        self.date_combo.currentTextChanged.connect(self._on_date_changed)
        btn_delete_date = Button('', fixed_width=30, fixed_height=30)
        btn_delete_date.setIcon(QIcon('images/delete.png'))
        btn_delete_date.clicked.connect(self.on_remove_date)

        date_row.addWidget(Label("Дата:"))
        date_row.addWidget(self.date_combo)
        date_row.addWidget(btn_delete_date)
        left_layout.addLayout(date_row)

        # 2. Набор (Set)
        set_row = QHBoxLayout()
        set_row.addWidget(Label("Набор:"))
        self.combo_set = ComboList(fixed_width=100)
        self.combo_set.currentIndexChanged.connect(self._on_set_changed)

        btn_add_set = Button("", fixed_width=30, fixed_height=30)
        btn_add_set.setIcon(QIcon('images/add.png'))
        btn_add_set.clicked.connect(self.on_add_set)

        btn_delete_set = Button("", fixed_width=30, fixed_height=30)
        btn_delete_set.setIcon(QIcon('images/delete.png'))
        btn_delete_set.clicked.connect(self.on_remove_set)

        set_row.addWidget(self.combo_set)
        set_row.addWidget(btn_add_set)
        set_row.addWidget(btn_delete_set)
        left_layout.addLayout(set_row)

        # 3. Схема призов
        win_row = QHBoxLayout()
        win_row.addWidget(Label("Схема призов:"))
        self.win_combo = ComboList(fixed_width=105)
        self.win_combo.addItems(self.winning_data.keys())
        self.win_combo.currentTextChanged.connect(self._on_win_set_changed)
        win_row.addWidget(self.win_combo)
        left_layout.addLayout(win_row)

        left_layout.addSpacing(12)

        # 4. Радиокнопки выбора билета
        self.color_buttons: List[QRadioButton] = []
        for i, color in enumerate(COLORS):
            rb = QRadioButton(f'Билет {i + 1} (0/7 + 0)')
            rb.setAutoExclusive(True)
            rb.setStyleSheet(
                f'background-color: {color.name()}; padding: 6px; '
                f'color: #203764; border: 1px solid #888; font-size: 16px; font-weight: bold; '
            )
            rb.clicked.connect(lambda _, idx=i: self._set_color(idx))  # type: ignore
            self.color_buttons.append(rb)
            left_layout.addWidget(rb)
        self.color_buttons[0].setChecked(True)

        left_layout.addSpacing(12)

        # 5. Кнопки управления
        self.btn_generate = Button("Генерировать")
        self.btn_generate.clicked.connect(self.on_generate)

        self.btn_generate_all = Button("Генерировать все")
        self.btn_generate_all.clicked.connect(self.on_generate_all)

        self.btn_save_set = Button("Сохранить")
        self.btn_save_set.clicked.connect(self.on_save)

        self.btn_back = Button("Назад")
        self.btn_back.clicked.connect(self.open_main_window)

        left_layout.addWidget(self.btn_generate)
        left_layout.addWidget(self.btn_generate_all)
        left_layout.addWidget(self.btn_save_set)
        left_layout.addWidget(self.btn_back)

        # === Правая панель ===
        right = QWidget()
        right_layout = QVBoxLayout()
        right.setLayout(right_layout)

        # Карточка 1
        self.card1 = CardWidget(rows=4, cols=9, active=CARD1_SIZE)
        self.card1.cell_clicked.connect(self.on_card1_click)  # type: ignore
        right_layout.addWidget(self.card1)

        right_layout.addStretch()

        # Стоимость
        cost_row = QHBoxLayout()
        cost_row.addWidget(Label('Цена билета'))
        self.cost_spin = EditSpin(fixed_width=50)
        self.cost_spin.textChanged.connect(self._on_cost_changed)
        cost_row.addWidget(self.cost_spin)
        cost_row.addSpacing(20)
        self.total_cost_label = Label('Общая стоимость = 0')
        cost_row.addWidget(self.total_cost_label)
        cost_row.addStretch()
        right_layout.addLayout(cost_row)

        right_layout.addStretch()

        # Карточка 2
        self.card2 = CardWidget(rows=6, cols=9, active=CARD2_SIZE)
        self.card2.cell_clicked.connect(self.on_card2_click)  # type: ignore
        right_layout.addWidget(self.card2)

        main_layout.addWidget(left, stretch=1)
        main_layout.addWidget(right, stretch=4)
        self.setLayout(main_layout)

    # ── Логика переключения даты и набора ──

    def _refresh_dates(self):
        dates = sorted(self.tickets_data.keys(), reverse=True, key=lambda d: dt.strptime(d, '%d.%m.%y'))
        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        self.date_combo.addItems(dates)
        if dates and not self.first_time:
            self.date_combo.setCurrentIndex(0)
            self.current_date = dates[0]
        else:
            self.current_date = None
            self.date_combo.setCurrentText('')
            self.first_time = False
        self.date_combo.blockSignals(False)
        self._load_current_context()

    def _on_date_changed(self, text: str):
        new_date = text.strip() if text else None
        old_date = self.current_date
        self.current_date = new_date
        self.excluded_nums = self.calc_top_nums()
        self.check_changes(old_date)
        self._load_current_context()

    def on_remove_date(self):
        if not self.current_date or self.current_date not in self.tickets_data:
            return
        reply = QMessageBox.question(self, 'Удаление билетов',
                                     f'Вы действительно хотите удалить все билеты\nза {self.current_date}?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        del self.tickets_data[self.current_date]
        save_all_tickets(self.tickets_data)

        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        self.date_combo.addItems(
            sorted(self.tickets_data.keys(), reverse=True, key=lambda d: dt.strptime(d, '%d.%m.%y')))
        self.date_combo.blockSignals(False)
        self.current_date = None
        self.date_combo.setCurrentText('')

    def _load_current_context(self):
        """Загружает данные для выбранной даты, набора, стоимости и выигрышей"""
        self.combo_set.blockSignals(True)
        self.cost_spin.blockSignals(True)
        self.combo_set.clear()

        if self.combo_set.count() == 0:
            self.combo_set.addItem(f"Набор 1")

        if not self.current_date or self.current_date not in self.tickets_data:
            # Пустая дата
            self._clear_cards()
            self._update_radio_buttons()
            self._update_cost()
            self.combo_set.blockSignals(False)
            self.cost_spin.blockSignals(False)
            return

        data = self.tickets_data[self.current_date]

        # Устанавливаем схему выигрыша
        win_set_name = data.win_set
        if win_set_name not in self.winning_data:
            self.winning_data[win_set_name] = Winning(name=win_set_name, sets={})
            self.win_combo.addItem(win_set_name)
        self.win_combo.setCurrentText(win_set_name)

        # Заполняем комбобокс наборами
        if data.sets:
            for i in range(1, len(data.sets)):
                self.combo_set.addItem(f"Набор {i + 1}")

        if len(data.sets) > 0:
            self.combo_set.setCurrentIndex(0)
            self._apply_set_data(0)
        else:
            self._clear_cards()

        self.combo_set.blockSignals(False)
        self.cost_spin.blockSignals(False)
        self._update_radio_buttons()
        self._update_cost()

        # Делаем снапшот
        if self.current_date and self.current_date in self.tickets_data:
            self.original_data = deepcopy(self.tickets_data[self.current_date])
        else:
            self.original_data = None

    def _on_set_changed(self, index: int):
        if self.current_date and self.current_date in self.tickets_data:
            self.current_set_index = index
            self._apply_set_data(index)
            self._update_radio_buttons()

    def _on_win_set_changed(self):
        if self.current_date and self.current_date in self.tickets_data:
            self.tickets_data[self.current_date].win_set = self.win_combo.currentText()

    def _on_cost_changed(self):
        if self.current_date and self.current_date in self.tickets_data:
            self.tickets_data[self.current_date].cost = self.cost_spin.value()
        self._update_total_cost_text()

    def _apply_set_data(self, set_idx: int):
        data = self.tickets_data[self.current_date]
        tickets = data.get_current_tickets(set_idx)

        # Очищаем локальные массивы
        self.first_card = [0] * CARD1_SIZE
        self.second_card = [0] * CARD2_SIZE

        # Заполняем из билетов этого набора
        for t in tickets:
            for idx in t.first_card_selected:
                if 0 <= idx < CARD1_SIZE:
                    self.first_card[idx] = t.ticket
            if t.second_card_selected is not None:
                self.second_card[t.second_card_selected] = t.ticket

        self._render_cards()

    # ── Действия с наборами ──

    def on_add_set(self):
        if not self.current_date:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите или введите дату!")
            return

        if self.current_date not in self.tickets_data:
            self.tickets_data[self.current_date] = TicketSets(date=self.current_date,
                                                              win_set=self.win_combo.currentText(),
                                                              cost=self.cost_spin.value())

        # Проверка, что последний набор полностью заполнен
        data = self.tickets_data[self.current_date].sets[-1]
        sets = len(self.tickets_data[self.current_date].sets)
        tickets = sum([1 for t in data if t.is_valid()])
        if tickets < 5:
            tickets = choose_plural(tickets, ('билет', 'билета', 'билетов'))
            QMessageBox.warning(self, "Ошибка",
                                "Сначала заполните полностью все 5 билетов в последнем наборе!"
                                f"\nСейчас в наборе {sets} полностью заполнено всего {tickets}.")
            return

        self.tickets_data[self.current_date].add_empty_set()

        # Перезагружаем контекст, чтобы обновить комбо и выбрать новый набор
        self._load_current_context()
        last_idx = len(self.tickets_data[self.current_date].sets) - 1
        self.combo_set.setCurrentIndex(last_idx)
        self.current_set_index = last_idx
        self._update_total_cost_text()

    def on_remove_set(self):
        if not self.current_date or self.current_date not in self.tickets_data:
            return

        data = self.tickets_data[self.current_date]
        count = len(data.sets)

        if count == 0:
            return

        if count == 1:
            # Если один набор - просто очищаем его и оставляем пустым
            data.sets[0] = []
            self._clear_cards()
            self._update_radio_buttons()
            self._update_total_cost_text()
            self.original_data = deepcopy(data)
            return

        # Удаляем текущий набор
        data.remove_set(self.current_set_index)
        tmp = deepcopy(self.original_data)  # сохраняем состояние до удаления

        # Обновляем UI
        new_index = min(self.current_set_index, len(data.sets) - 1)
        self._load_current_context()  # Полная перезагрузка комбо
        self.combo_set.setCurrentIndex(new_index)
        self.current_set_index = new_index
        self._update_total_cost_text()
        self.original_data = tmp  # фиксируем отсутствие удаления в оригинале

    # ── Вспомогательные методы UI ──

    def calc_top_nums(self) -> Optional[List[List[int]]]:
        if len(self.results_data) == 0:
            return None
        dates = sorted(self.results_data.keys(), reverse=True, key=lambda d: dt.strptime(d, '%d.%m.%y'))
        cur_date = self.current_date if is_valid_date(self.current_date) else dt.now().strftime('%d.%m.%y')
        dates = list(filter(lambda d: dt.strptime(d, '%d.%m.%y') < dt.strptime(cur_date, '%d.%m.%y'), dates))
        nums = [self.results_data[d].second_card_selected for d in dates
                if self.results_data[d].second_card_selected is not None][:30]
        if not nums:
            return None
        unic_nums = list({n: None for n in nums})
        nums_dict = {num: 1 if i < 3 else round(1 - (i - 2) * 0.05, 2) if i < 20 else 0.1
                     for i, num in enumerate(unic_nums)}
        nums_dict = {k: round(v * nums.count(k), 2) for k, v in nums_dict.items()}
        top_nums = list(dict(sorted(nums_dict.items(), reverse=True, key=lambda x: x[1])))
        top_nums = [top_nums[:5], top_nums[5:20]]
        return top_nums

    def _highlight_excluded_nums(self):
        """Подсвечивает числа второй карточки: топ-5 — красным, следующие 15 — оранжевым"""
        if not self.excluded_nums:
            return
        for idx in self.excluded_nums[0]:
            if 0 <= idx < CARD2_SIZE:
                change_style(self.card2.buttons[idx], 'color', 'red')
        for idx in self.excluded_nums[1]:
            if 0 <= idx < CARD2_SIZE:
                change_style(self.card2.buttons[idx], 'color', 'orange')

    def _highlight_already_selected_nums(self):
        """Подсвечивает числа второй карточки зеленым, если число уже выбрано в другом наборе"""
        if (not self.current_date or
                self.current_date not in self.tickets_data or
                len(self.tickets_data[self.current_date].sets) < 2):
            return
        for idx in range(len(self.tickets_data[self.current_date].sets)):
            if idx != self.current_set_index:
                for num in [t.second_card_selected for t in self.tickets_data[self.current_date].sets[idx]]:
                    if 0 <= num < CARD2_SIZE:
                        change_style(self.card2.buttons[num], 'color', 'green')

    def _set_color(self, idx: int):
        self.selected_ticket_index = idx
        self._update_radio_buttons()

    def _clear_cards(self):
        self.first_card = [0] * CARD1_SIZE
        self.second_card = [0] * CARD2_SIZE
        self._render_cards()

    def _render_cards(self):
        for i in range(CARD1_SIZE):
            v = self.first_card[i]
            self.card1.set_cell_color(i, COLORS[v - 1] if v > 0 else None)
        for i in range(CARD2_SIZE):
            v = self.second_card[i]
            self.card2.set_cell_color(i, COLORS[v - 1] if v > 0 else None)
        self._highlight_excluded_nums()
        self._highlight_already_selected_nums()

    def _update_radio_buttons(self):
        """Обновляет текст на радиокнопках в формате: Билет N (X/7 + Y) и показывает цветом валидность"""
        for ticket_idx in range(5):
            ticket = ticket_idx + 1
            c1 = sum(1 for v in self.first_card if v == ticket)
            c2 = sum(1 for v in self.second_card if v == ticket)
            text = f"Билет {ticket_idx + 1} ({c1}/7 + {c2})"
            self.color_buttons[ticket_idx].setText(text)
            color = 'green' if c1 + c2 == 8 else 'red'
            change_style(self.color_buttons[ticket_idx], 'color', color)

    def _update_cost(self):
        """Обновляет данные по стоимости"""
        if self.current_date and self.current_date in self.tickets_data:
            self.cost_spin.setValue(self.tickets_data[self.current_date].cost)
        else:
            self.cost_spin.setValue(0)
        self._update_total_cost_text()

    def _update_total_cost_text(self):
        cost = self.calculate_total_cost()
        self.total_cost_label.setText(f'Общая стоимость = {cost}🥕')

    def calculate_total_cost(self) -> int:
        if not self.current_date or self.current_date not in self.tickets_data:
            return 0
        cost = self.cost_spin.value()
        tickets = 0
        for s in self.tickets_data[self.current_date].sets:
            tickets += sum([1 for t in s if t.is_valid()])
        return cost * tickets

    # ── Клик по первой карточке ──

    def on_card1_click(self, idx: int):
        if not (0 <= idx < CARD1_SIZE):
            return
        ticket = self.selected_ticket_index + 1

        if self.first_card[idx] == ticket:
            self.first_card[idx] = 0
        else:
            count = sum(1 for v in self.first_card if v == ticket)
            if count >= 7:
                QMessageBox.information(self, "Внимание", "Все ячейки уже выбраны!")
                return
            self.first_card[idx] = ticket

        self._render_cards()
        self._update_radio_buttons()
        self._sync_to_data()
        self._update_total_cost_text()

    # ── Клик по второй карточке ──

    def on_card2_click(self, idx: int):
        if not (0 <= idx < CARD2_SIZE):
            return
        ticket = self.selected_ticket_index + 1

        if self.second_card[idx] == ticket:
            self.second_card[idx] = 0
        else:
            for i in range(CARD2_SIZE):
                if self.second_card[i] == ticket:
                    self.second_card[i] = 0
            self.second_card[idx] = ticket

        self._render_cards()
        self._update_radio_buttons()
        self._sync_to_data()
        self._update_total_cost_text()

    def _check_validity(self) -> bool:
        if not self.current_date:
            QMessageBox.warning(self, "Ошибка", "Укажите дату!")
            return False
        if not is_valid_date(self.current_date):
            QMessageBox.warning(self, "Ошибка", "Некорректная дата! Используйте dd.mm.yy")
            return False
        return True

    # ── Генерация ──

    def _generator(self, ticket: int):
        # Очистить только текущий цвет
        self.first_card = [0 if v == ticket else v for v in self.first_card]
        self.second_card = [0 if v == ticket else v for v in self.second_card]

        free1 = [i for i, v in enumerate(self.first_card) if v == 0]
        free2 = [i for i, v in enumerate(self.second_card) if v == 0]

        if len(free1) < 7:
            QMessageBox.warning(self, "Ошибка", "Недостаточно свободных ячеек в первой карточке!")
            self._render_cards()
            self._update_radio_buttons()
            return
        if len(free2) < 1:
            QMessageBox.warning(self, "Ошибка", "Недостаточно свободных ячеек во второй карточке!")
            self._render_cards()
            self._update_radio_buttons()
            return

        for idx in random.sample(free1, 7):
            self.first_card[idx] = ticket

        # --- Отбор свободных ячеек для второй карточки ---
        # Убираем числа, выбранные в других наборах
        for idx in range(len(self.tickets_data[self.current_date].sets)):
            if idx != self.current_set_index:
                second_card_selected = [t.second_card_selected for t in self.tickets_data[self.current_date].sets[idx]]
                if len(free2) > len(second_card_selected):
                    free2 = [f for f in free2 if f not in second_card_selected]

        # Убираем числа, ранее выпавшие в результатах
        if len(free2) > len(self.excluded_nums[0]):
            free2 = [f for f in free2 if f not in self.excluded_nums[0]]
            if len(free2) > len(self.excluded_nums[1]):
                free2 = [f for f in free2 if f not in self.excluded_nums[1]]

        self.second_card[random.choice(free2)] = ticket

        self._render_cards()
        self._update_radio_buttons()
        self._sync_to_data()

    def on_generate(self):
        if not self._check_validity():
            return
        self._sync_to_data()
        self._generator(self.selected_ticket_index + 1)
        self._update_total_cost_text()

    def on_generate_all(self):
        if not self._check_validity():
            return
        self._clear_cards()
        self._sync_to_data()
        for i in range(1, 6):
            self._generator(i)
        self._update_total_cost_text()

    def _sync_to_data(self):
        """Записывает текущее состояние карточек в self.tickets_data"""
        if not self.current_date:
            return

        if self.current_date not in self.tickets_data:
            self.tickets_data[self.current_date] = TicketSets(date=self.current_date,
                                                              win_set=self.win_combo.currentText(),
                                                              cost=self.cost_spin.value())

        data = self.tickets_data[self.current_date]

        if not data.sets:
            data.add_empty_set()
            self.current_set_index = 0

        tickets: List[Ticket] = []
        for ticket in range(1, 6):
            first_indices = [i for i, v in enumerate(self.first_card) if v == ticket]
            second_idx = next((i for i, v in enumerate(self.second_card) if v == ticket), None)
            if first_indices or second_idx is not None:
                tickets.append(Ticket(ticket=ticket,
                                      first_card_selected=first_indices,
                                      second_card_selected=second_idx))

        data.sets[self.current_set_index] = tickets

    # ── Сохранение ──

    def on_save(self, date: str = None):
        if not self._check_validity():
            return

        save_date = date or self.current_date
        data = self.tickets_data[save_date]

        if not data.is_valid():
            errors = []
            if not is_valid_date(data.date):
                errors.append("Некорректная дата.")
            for i, s in enumerate(data.sets[:-1]):
                if not data.is_set_full(s):
                    errors.append(f"Набор {i + 1} заполнен не полностью (нужно 5 валидных билетов).")
            if not any(t.is_valid() for t in data.sets[-1]):
                errors.append("В последнем наборе не все билеты заполнены 7+1.")
            if not data.cost:
                errors.append('Укажите цену билетов.')
            QMessageBox.warning(self, "Ошибка валидации", '\n'.join(errors))
            return

        save_all_tickets(self.tickets_data)

        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        self.date_combo.addItems(sorted(self.tickets_data.keys(), reverse=True,
                                        key=lambda d: dt.strptime(d, '%d.%m.%y')))
        self.date_combo.setCurrentText(self.current_date)
        self.date_combo.blockSignals(False)

        self.combo_set.setCurrentIndex(self.current_set_index)

        # Обновляем снапшот только если сохранили именно текущую дату
        if save_date == self.current_date and self.current_date in self.tickets_data:
            self.original_data = deepcopy(self.tickets_data[self.current_date])

        QMessageBox.information(self, 'Успешно', f'Данные сохранены в {TICKETS_FILE}')

    def check_changes(self, old_date: str):
        """Проверка на несохраненные изменения"""
        if not old_date or old_date not in self.tickets_data:
            return

        if self.tickets_data[old_date] != self.original_data:
            reply = QMessageBox.question(self, 'Данные изменены',
                                         f'Есть изменения в данных!\nСохранить изменения перед продолжением?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.on_save(old_date)

    def closeEvent(self, event):
        self.check_changes(self.current_date)
        event.accept()

    def open_main_window(self):
        self.check_changes(self.current_date)
        self.window = WelcomeWindow()
        self.window.show()
        self.close()


class ResultWindow(Window):
    def __init__(self, date: str = ''):
        super().__init__('Результаты', width=800, height=600)
        self.results_data: Dict[str, Result] = load_all_results()
        self.ticket_data: Dict[str, TicketSets] = load_all_tickets()
        self.winning_data: Dict[str, Winning] = load_all_winnings()
        self.current_date: Optional[str] = None

        # Состояние результата: выбранные ячейки
        self.result_first: set = set()
        self.result_second: Optional[int] = None

        self._init_ui()
        if date:
            self.date_combo.setCurrentText(date)

    def _init_ui(self):
        main_layout = QHBoxLayout()

        # === Левая панель ===
        left = QWidget()
        left_layout = QVBoxLayout()
        left.setLayout(left_layout)

        # Дата
        date_row = QHBoxLayout()
        self.date_combo = ComboList(fixed_width=105, editable=True, date_mask=True)
        dates = sorted(self.results_data.keys(), reverse=True, key=lambda d: dt.strptime(d, '%d.%m.%y'))
        self.date_combo.addItems(dates)
        self.date_combo.setCurrentText('')
        self.date_combo.currentTextChanged.connect(self._on_date_changed)

        btn_delete_date = Button('', fixed_width=30, fixed_height=30)
        btn_delete_date.setIcon(QIcon('images/delete.png'))
        btn_delete_date.clicked.connect(self.on_remove_date)

        date_row.addWidget(Label("Дата:"))
        date_row.addWidget(self.date_combo)
        date_row.addWidget(btn_delete_date)
        left_layout.addLayout(date_row)

        # Схема призов
        win_row = QHBoxLayout()
        win_row.addWidget(Label("Схема призов:"))
        self.win_combo = ComboList(fixed_width=105)
        self.win_combo.addItems(self.winning_data.keys())
        self.win_combo.currentTextChanged.connect(self._on_win_set_changed)
        win_row.addWidget(self.win_combo)
        left_layout.addLayout(win_row)

        left_layout.addSpacing(12)

        # Зона с кнопками-совпадениями (прокручиваемая)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(250)
        scroll_content = QWidget()
        self.buttons_layout = QVBoxLayout(scroll_content)
        self.buttons_layout.addStretch()
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll, stretch=1)

        # Кнопки
        self.btn_save = Button("Сохранить")
        self.btn_save.clicked.connect(self.on_save)
        left_layout.addWidget(self.btn_save)

        self.btn_back = Button("Назад")
        self.btn_back.clicked.connect(self.open_main_window)
        left_layout.addWidget(self.btn_back)

        # === Правая панель ===
        right = QWidget()
        right_layout = QVBoxLayout()
        right.setLayout(right_layout)

        self.card1 = CardWidget(rows=4, cols=9, active=CARD1_SIZE)
        self.card1.cell_clicked.connect(self.on_card1_click)  # type: ignore
        right_layout.addWidget(self.card1)

        right_layout.addStretch()

        self.selected_label = Label('')
        right_layout.addWidget(self.selected_label)

        self.result_label = Label('')
        right_layout.addWidget(self.result_label)

        right_layout.addStretch()

        self.card2 = CardWidget(rows=6, cols=9, active=CARD2_SIZE)
        self.card2.cell_clicked.connect(self.on_card2_click)  # type: ignore
        right_layout.addWidget(self.card2)

        main_layout.addWidget(left, stretch=1)
        main_layout.addWidget(right, stretch=4)
        self.setLayout(main_layout)

    # ── Переключение даты ──

    def _on_date_changed(self, text: str):
        new_date = text.strip() if text else None
        old_date = self.current_date
        self.current_date = new_date
        self.check_changes(old_date)
        self._load_result()
        if new_date and new_date in self.results_data:
            self.win_combo.setCurrentText(self.results_data[new_date].win_set)
        if new_date and new_date in self.ticket_data:
            self.win_combo.setCurrentText(self.ticket_data[new_date].win_set)
            self.win_combo.setEnabled(False)
        else:
            self.win_combo.setEnabled(True)
        self._update_labels()

    def on_remove_date(self):
        if not self.current_date or self.current_date not in self.results_data:
            return
        reply = QMessageBox.question(self, 'Удаление результата',
                                     f'Вы действительно хотите удалить результат\nза {self.current_date}?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        del self.results_data[self.current_date]
        save_all_results(self.results_data)

        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        self.date_combo.addItems(
            sorted(self.results_data.keys(), reverse=True, key=lambda d: dt.strptime(d, '%d.%m.%y')))
        self.date_combo.blockSignals(False)
        self.current_date = None
        self.date_combo.setCurrentText('')

    def _on_win_set_changed(self):
        self._rebuild_buttons()

    def _load_result(self):
        self.result_first = set()
        self.result_second = None
        self._clear_cards()
        self._clear_outlines()
        self._clear_buttons()

        if not self.current_date or self.current_date not in self.results_data:
            return

        result = self.results_data[self.current_date]
        self.result_first = set(result.first_card_selected)
        self.result_second = result.second_card_selected
        self._render_cards()
        self._rebuild_buttons()

    # ── Рендеринг карточек ──

    def _clear_cards(self):
        for i in range(CARD1_SIZE):
            self.card1.set_cell_color(i, None)
        for i in range(CARD2_SIZE):
            self.card2.set_cell_color(i, None)

    def _render_cards(self):
        for idx in self.result_first:
            if 0 <= idx < CARD1_SIZE:
                self.card1.set_cell_color(idx, RESULT_COLOR)
        if self.result_second is not None and 0 <= self.result_second < CARD2_SIZE:
            self.card2.set_cell_color(self.result_second, RESULT_COLOR)

    # ── Очистка обводок и кнопок ──

    def _clear_outlines(self):
        self.card1.clear_all_borders()
        self.card2.clear_all_borders()

    def _clear_buttons(self):
        """Удаляет все кнопки-совпадения, оставляя stretch"""
        while self.buttons_layout.count() > 1:
            item = self.buttons_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # ── Клик по карточкам результата ──

    def on_card1_click(self, idx: int):
        if not (0 <= idx < CARD1_SIZE):
            return

        self._clear_outlines()

        if idx in self.result_first:
            self.result_first.remove(idx)
            self.card1.set_cell_color(idx, None)
        else:
            if len(self.result_first) >= 7:
                QMessageBox.information(self, "Внимание", "Все ячейки уже выбраны!")
                return
            self.result_first.add(idx)
            self.card1.set_cell_color(idx, RESULT_COLOR)

        self._rebuild_buttons()

    def on_card2_click(self, idx: int):
        if not (0 <= idx < CARD2_SIZE):
            return

        self._clear_outlines()

        if self.result_second == idx:
            self.result_second = None
            self.card2.set_cell_color(idx, None)
        else:
            if self.result_second is not None:
                self.card2.set_cell_color(self.result_second, None)
            self.result_second = idx
            self.card2.set_cell_color(idx, RESULT_COLOR)

        self._rebuild_buttons()

    # ── Построение кнопок-совпадений ──

    def _rebuild_buttons(self):
        self._clear_buttons()
        self._update_labels()

        if not self.current_date or self.current_date not in self.ticket_data:
            return

        ts = self.ticket_data[self.current_date]
        result_first_set = self.result_first
        result_second = self.result_second
        win_scheme = self.winning_data[self.win_combo.currentText()]

        # Индексы ключей в схеме выигрышей: чем больше индекс — тем ценнее
        win_keys = list(win_scheme.sets.keys())
        win_index = {key: i for i, key in enumerate(win_keys)}

        # 1. Собираем выигрышные билеты с индексом выигрыша
        winners = []  # (win_idx, set_idx, ticket, x, y, win_result)
        for set_idx, ticket_set in enumerate(ts.sets):
            for ticket in ticket_set:
                ticket_first = set(ticket.first_card_selected)
                x = len(ticket_first & result_first_set)
                y = 1 if (ticket.second_card_selected is not None and
                          ticket.second_card_selected == result_second) else 0

                if x >= 2 or y >= 1:
                    win_result = win_scheme.sets[(x, y)]
                    idx = win_index[(x, y)]
                    winners.append((idx, set_idx, ticket, x, y, win_result))

        # 2. Сортируем: по убыванию индекса (ценнее — выше), при равенстве — исходный порядок
        winners.sort(key=lambda w: w[0], reverse=True)

        # 3. Создаём кнопки
        for _, set_idx, ticket, x, y, win_result in winners:
            color = COLORS[ticket.ticket - 1]
            text = (f"Набор {set_idx + 1}/билет {ticket.ticket}: "
                    f"{x}+{y}={win_result[0]:,d}{win_result[1]}")
            btn = Button(text)
            btn.setStyleSheet(
                f"font-size: 14px; font-weight: bold; color: #203764; "
                f"border: 1px solid #888; border-radius: 4px; "
                f"background-color: {color.name()}; padding: 6px;"
            )
            btn.clicked.connect(lambda _, t=ticket: self._show_ticket_outline(t))
            self.buttons_layout.insertWidget(self.buttons_layout.count() - 1, btn)

    def _show_ticket_outline(self, ticket: Ticket):
        self._clear_outlines()
        color = COLORS[ticket.ticket - 1].name()
        for idx in ticket.first_card_selected:
            if 0 <= idx < CARD1_SIZE:
                self.card1.set_cell_border(idx, color)
        if ticket.second_card_selected is not None and 0 <= ticket.second_card_selected < CARD2_SIZE:
            self.card2.set_cell_border(ticket.second_card_selected, color)

    # ── Текст выбора и результатов ──

    def _update_labels(self):
        if not self.current_date:
            self.selected_label.setText('')
            self.result_label.setText('')
            return

        self.selected_label.setText(f'Выбрано: {len(self.result_first)}/7 + {int(self.result_second is not None)}')
        color = 'red' if len(self.result_first) < 7 or self.result_second is None else 'green'
        change_style(self.selected_label, 'color', color)

        if self.current_date not in self.ticket_data:
            self.result_label.setText('')
            return

        win_data = self.winning_data[self.win_combo.currentText()]
        ticket_data = self.ticket_data[self.current_date]
        if self.current_date not in self.results_data:
            res_data = Result(self.current_date,
                              self.win_combo.currentText(),
                              list(self.result_first),
                              self.result_second)
        else:
            res_data = self.results_data[self.current_date]
        won_m, won_b, spent = res_data.calculate_winnings_for_tickets(win_data, ticket_data)

        won_text = f'{won_m:,d}🥕, ' if won_m else ''
        won_text += f'{won_b:,d}💵' if won_b else ''
        if won_m or won_b:
            self.result_label.setText(f'Потрачено: {spent:,d}🥕, выиграно {won_text.strip(", ")}')
        else:
            self.result_label.setText(f'Потрачено: {spent:,d}🥕')

    # ── Сохранение ──

    def on_save(self, date: str = None):
        error_text = []
        if not self.current_date:
            error_text = ["Укажите дату!"]
        if self.current_date and not is_valid_date(self.current_date):
            error_text.append("Некорректная дата! Используйте dd.mm.yy")
        if len(self.result_first) < 7:
            error_text.append('В первой карточке должно быть выделено 7 ячеек!')
        if self.result_second is None:
            error_text.append('Укажите ячейку во второй карточке!')
        if error_text:
            QMessageBox.warning(self, "Ошибка", '\n'.join(error_text))
            return

        save_date = date or self.current_date
        result = Result(
            date=save_date,
            win_set=self.win_combo.currentText(),
            first_card_selected=sorted(self.result_first),
            second_card_selected=self.result_second
        )
        self.results_data[save_date] = result
        save_all_results(self.results_data)

        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        self.date_combo.addItems(
            sorted(self.results_data.keys(), reverse=True, key=lambda d: dt.strptime(d, '%d.%m.%y')))
        self.date_combo.setCurrentText(self.current_date)
        self.date_combo.blockSignals(False)

        QMessageBox.information(self, "Успешно", f"Результат сохранён в {RESULTS_FILE}")

    def check_changes(self, old_date: str):
        """Проверка на несохраненные изменения"""
        reply = None
        date = old_date
        win_set = self.win_combo.currentText()
        first_result = sorted(list(self.result_first))
        second_result = self.result_second
        result = Result(date, win_set, first_result, second_result)
        if old_date and old_date in self.results_data:
            if self.results_data[old_date] != result:
                reply = QMessageBox.question(self, 'Данные изменены',
                                             f'Есть изменения в данных!\nСохранить изменения перед продолжением?',
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        elif result.is_valid():
            reply = QMessageBox.question(self, 'Новый результат не сохранен',
                                         f'Новый результат может быть потерян!\nСохранить результат перед продолжением?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.on_save(old_date)

    def closeEvent(self, event):
        self.check_changes(self.current_date)
        event.accept()

    def open_main_window(self):
        self.check_changes(self.current_date)
        self.window = WelcomeWindow()
        self.window.show()
        self.close()


class WinningWindow(Window):
    def __init__(self):
        super().__init__('Схемы призов', width=700, height=600)
        self.winning_data: Dict[str, Winning] = load_all_winnings()
        self.tickets_data: Dict[str, TicketSets] = load_all_tickets()
        self.results_data: Dict[str, Result] = load_all_results()
        self.original_data = None
        self.trigger_to_save = False  # при любом изменении становится True

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout()

        # === Верхняя часть: две панели рядом ===
        panels_layout = QHBoxLayout()

        # --- Левая панель: список схем ---
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)

        # --- Схема призов - кнопки ---
        left_btn_layout = QHBoxLayout()
        left_btn_layout.addWidget(Label("Схемы призов"))

        btn_add_winning = Button('', fixed_width=30, fixed_height=30)
        btn_add_winning.setIcon(QIcon('images/add.png'))
        btn_add_winning.clicked.connect(self.on_add_winning)

        btn_copy_winning = Button('', fixed_width=30, fixed_height=30)
        btn_copy_winning.setIcon(QIcon('images/copy.png'))
        btn_copy_winning.clicked.connect(self.on_copy_winning)

        btn_rename_winning = Button('', fixed_width=30, fixed_height=30)
        btn_rename_winning.setIcon(QIcon('images/rename.png'))
        btn_rename_winning.clicked.connect(self.on_rename_winning)

        btn_del_winning = Button('', fixed_width=30, fixed_height=30)
        btn_del_winning.setIcon(QIcon('images/delete.png'))
        btn_del_winning.clicked.connect(self.on_remove_winning)

        left_btn_layout.addWidget(btn_add_winning)
        left_btn_layout.addWidget(btn_copy_winning)
        left_btn_layout.addWidget(btn_rename_winning)
        left_btn_layout.addWidget(btn_del_winning)
        left_layout.addLayout(left_btn_layout)

        self.list_winnings = QListWidget()
        self.list_winnings.setStyleSheet('color: #203764; font-size: 16px')
        self.list_winnings.currentRowChanged.connect(self._on_selection_changed)  # type: ignore
        left_layout.addWidget(self.list_winnings)

        panels_layout.addWidget(left_panel, stretch=1)

        # --- Правая панель: редактирование ---
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)

        # Кнопки сверху
        btn_row = QHBoxLayout()

        self.btn_save_set = Button("Сохранить", fixed_width=180)
        self.btn_save_set.clicked.connect(self.on_save_winning)
        btn_row.addWidget(self.btn_save_set)

        btn_back = Button("Назад", fixed_width=180)
        btn_back.clicked.connect(self.open_main_window)
        btn_row.addWidget(btn_back)

        right_layout.addLayout(btn_row)

        # Таблица вариантов
        self.table_sets = QTableWidget()
        self.table_sets.setStyleSheet('color: #203764; font-size: 16px')
        self.table_sets.setColumnCount(3)
        self.table_sets.setHorizontalHeaderLabels(["Вариант", "Номинал", "Тип"])
        self.table_sets.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table_sets.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_sets.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table_sets.setColumnWidth(0, 200)
        self.table_sets.setColumnWidth(2, 80)
        self.table_sets.itemChanged.connect(self._on_nominal_changed)  # type: ignore
        self.table_sets.itemClicked.connect(self._on_type_cell_clicked)  # type: ignore
        right_layout.addWidget(self.table_sets)

        panels_layout.addWidget(right_panel, stretch=2)
        main_layout.addLayout(panels_layout, stretch=1)

        self.setLayout(main_layout)
        self._refresh_list()

    # --- Логика ---

    @staticmethod
    def _generate_variant_text(x: int, y: int) -> str:
        return '🟡' * x + '🟣' * y

    def _refresh_list(self):
        self.list_winnings.blockSignals(True)
        self.list_winnings.clear()
        self.list_winnings.addItems(self.winning_data.keys())
        self.list_winnings.blockSignals(False)

    def _on_selection_changed(self, row: int):
        if row < 0 or row >= len(self.winning_data):
            self._clear_edit_form()
            return
        name = self.list_winnings.item(row).text()
        obj = self.winning_data[name]
        self._populate_sets_table(obj)

    def _clear_edit_form(self):
        self.table_sets.setRowCount(0)

    def _populate_sets_table(self, obj: 'Winning'):
        self.table_sets.blockSignals(True)
        self.table_sets.setRowCount(0)

        for (x, y), value in obj.sets.items():
            row = self.table_sets.rowCount()
            self.table_sets.insertRow(row)

            # Колонка 0: Вариант (нередактируемый)
            variant_text = self._generate_variant_text(x, y)
            variant_item = QTableWidgetItem(variant_text)
            variant_item.setFlags(variant_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            variant_item.setData(Qt.ItemDataRole.UserRole, (x, y))
            self.table_sets.setItem(row, 0, variant_item)

            # Колонка 1: Номинал — value[0] (число), 0 = пусто
            nominal = value[0] if isinstance(value, list) and len(value) >= 1 else 0
            nominal_str = str(nominal) if nominal else ""
            self.table_sets.setItem(row, 1, QTableWidgetItem(nominal_str))

            # Колонка 2: Тип — value[1] ('м.' / 'б.')
            prize_type = value[1] if isinstance(value, list) and len(value) >= 2 else 'м.'
            type_item = QTableWidgetItem()
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if prize_type == 'б.':
                type_item.setText('💵')
                type_item.setData(Qt.ItemDataRole.UserRole, 'б.')
            else:
                type_item.setText('🥕')
                type_item.setData(Qt.ItemDataRole.UserRole, 'м.')
            self.table_sets.setItem(row, 2, type_item)

        self.table_sets.blockSignals(False)

    def _on_nominal_changed(self, item: QTableWidgetItem):
        if item.column() != 1:
            return

        row = self.list_winnings.currentRow()
        if row < 0:
            return
        scheme_name = self.list_winnings.item(row).text()

        row_idx = item.row()
        variant_item = self.table_sets.item(row_idx, 0)
        if not variant_item:
            return
        coords = variant_item.data(Qt.ItemDataRole.UserRole)
        if not coords:
            return
        x, y = coords

        text = item.text().strip()
        scheme = self.winning_data.get(scheme_name)
        try:
            nominal = int(text) if text else 0
        except ValueError:
            # Восстанавливаем прежнее значение, если ввели не число
            if scheme and (x, y) in scheme.sets:
                old_val = scheme.sets[(x, y)][0]
                self.table_sets.blockSignals(True)
                item.setText(str(old_val) if old_val else "")
                self.table_sets.blockSignals(False)
            return

        if scheme and (x, y) in scheme.sets:
            scheme.sets[(x, y)][0] = nominal
        self.trigger_to_save = True

    def _on_type_cell_clicked(self, item: QTableWidgetItem):
        if item.column() != 2:
            return

        row = self.list_winnings.currentRow()
        if row < 0:
            return
        scheme_name = self.list_winnings.item(row).text()

        row_idx = item.row()
        variant_item = self.table_sets.item(row_idx, 0)
        if not variant_item:
            return
        coords = variant_item.data(Qt.ItemDataRole.UserRole)
        if not coords:
            return
        x, y = coords

        current = item.data(Qt.ItemDataRole.UserRole)
        if current == 'м.':
            new_type = 'б.'
            item.setText('💵')
        else:
            new_type = 'м.'
            item.setText('🥕')
        item.setData(Qt.ItemDataRole.UserRole, new_type)

        # Сохраняем напрямую в winning_data
        scheme = self.winning_data.get(scheme_name)
        if scheme and (x, y) in scheme.sets:
            scheme.sets[(x, y)][1] = new_type
        self.trigger_to_save = True

    def on_add_winning(self):
        base_name = dt.now().strftime('%d-%m-%y')
        name = base_name
        i = 2
        while name in self.winning_data:
            name = f"{base_name}_{i:02d}"
            i += 1
        name, ok = QInputDialog.getText(self, "Новая схема", "Введите название схемы:", text=name)
        name = name.strip()
        if not ok or not name:
            return
        if name in self.winning_data:
            QMessageBox.warning(self, "Ошибка", "Схема с таким именем уже существует.")
            return
        # Создаём схему с 14 готовыми вариантами: номинал пустой, тип — б.
        sets = {key: [0, 'б.'] for key in WINNING_VARIANTS}
        self.winning_data[name] = Winning(name=name, sets=sets)
        self._refresh_list()
        row = list(self.winning_data.keys()).index(name)
        self.list_winnings.setCurrentRow(row)
        self.trigger_to_save = True

    def on_copy_winning(self):
        row = self.list_winnings.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Копирование", "Сначала выберите схему для копирования.")
            return
        original_name = self.list_winnings.item(row).text()
        base_name = original_name
        # Подбираем уникальное имя: "Схема 40-2_copy", "Схема 40-2_copy2", ...
        copy_name = f"{base_name}_(01)"
        i = 2
        while copy_name in self.winning_data:
            copy_name = f"{base_name}_({i:02d})"
            i += 1

        name, ok = QInputDialog.getText(self, "Копирование схемы", "Введите название новой схемы:", text=copy_name)
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self.winning_data:
            QMessageBox.warning(self, "Ошибка", "Схема с таким именем уже существует.")
            return

        # Глубокая копия данных
        original = self.winning_data[original_name]
        copied_sets = {k: list(v) for k, v in original.sets.items()}
        self.winning_data[name] = Winning(name=name, sets=copied_sets)
        self._refresh_list()
        new_row = list(self.winning_data.keys()).index(name)
        self.list_winnings.setCurrentRow(new_row)
        self.trigger_to_save = True

    def on_rename_winning(self):
        row = self.list_winnings.currentRow()
        if row < 0:
            return
        name = self.list_winnings.item(row).text()

        # Проверка наличия схемы в результатах
        if any(map(lambda date: self.results_data[date].win_set == name, self.results_data)):
            reply = QMessageBox.question(self, "Наличие схемы в результатах",
                                         f"Вы действительно хотите переименовать схему «{name}»?\n"
                                         "Данная схема есть в результатах!",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return

        new_name, ok = QInputDialog.getText(self, "Переименование схемы",
                                            "Введите название для переименования:",
                                            text=name)
        new_name = new_name.strip()
        if not ok or not new_name:
            return
        if new_name in self.winning_data:
            QMessageBox.warning(self, "Ошибка", "Схема с таким именем уже существует.")
            return

        # Переименование схем в билетах
        for ticket in self.tickets_data:
            if self.tickets_data[ticket].win_set == name:
                self.tickets_data[ticket].win_set = new_name
        save_all_tickets(self.tickets_data)

        # Переименование схем в результатах
        for result in self.results_data:
            if self.results_data[result].win_set == name:
                self.results_data[result].win_set = new_name
        save_all_results(self.results_data)

        original = self.winning_data[name]
        copied_sets = {k: list(v) for k, v in original.sets.items()}
        self.winning_data[new_name] = Winning(name=new_name, sets=copied_sets)
        del self.winning_data[name]
        self._refresh_list()
        new_row = list(self.winning_data.keys()).index(new_name)
        self.list_winnings.setCurrentRow(new_row)

        self.trigger_to_save = True

    def on_remove_winning(self):
        row = self.list_winnings.currentRow()
        if row < 0:
            return
        name = self.list_winnings.item(row).text()

        # Проверка наличия схемы в результатах
        if any(map(lambda date: self.results_data[date].win_set == name, self.results_data)):
            QMessageBox.warning(self, "Невозможно удалить", "Сначала нужно удалить данные в результатах!")
            return

        # Проверка наличия схемы в билетах
        if any(map(lambda date: self.tickets_data[date].win_set == name, self.tickets_data)):
            QMessageBox.warning(self, "Невозможно удалить", "Сначала нужно удалить данные в билетах!")
            return

        reply = QMessageBox.question(self, "Удаление схемы",
                                     f"Вы действительно хотите удалить схему «{name}»?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        del self.winning_data[name]
        self._refresh_list()
        self._clear_edit_form()
        self.trigger_to_save = True

    def on_save_winning(self):
        # Проверка незаполненных номиналов
        for scheme in self.winning_data:
            if any(map(lambda s: s[0] == 0, self.winning_data[scheme].sets.values())):
                QMessageBox.warning(self, "Незаполненные данные",
                                    f"В схеме {scheme} есть варианты с нулевым номиналом!\n"
                                    "Все данные должны быть заполнены!")
                return

        save_all_winnings(self.winning_data)
        QMessageBox.information(self, "Успешно", f"Результат сохранён в {WINNINGS_FILE}")
        self.trigger_to_save = False

    def closeEvent(self, event):
        if not getattr(self, 'trigger_to_save', True):
            event.accept()
            return
        reply = QMessageBox.question(self, 'Данные изменены',
                                     f'Есть изменения в данных!\nСохранить изменения перед выходом?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.on_save_winning()
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            self.trigger_to_save = True
            event.accept()
        else:
            event.ignore()

    def open_main_window(self):
        if self.trigger_to_save:
            reply = QMessageBox.question(self, 'Данные изменены',
                                         f'Есть изменения в данных!\nСохранить изменения перед выходом?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.on_save_winning()

        self.window = WelcomeWindow()
        self.window.show()
        self.close()

    # @staticmethod
    # def open_editor(parent, all_winnings: Dict[str, 'Winning']) -> Optional[Dict[str, 'Winning']]:
    #     """Статический метод для удобного вызова из другого окна"""
    #     dialog = WinningEditorWindow(all_winnings)
    #     if dialog.exec() == QDialog.DialogCode.Accepted:
    #         return dialog.all_winnings
    #     return None


class StatisticWindow(Window):
    def __init__(self, date: str = ''):
        super().__init__("Статистика выигрышей по датам")
        self.results_data: Dict[str, Result] = load_all_results()
        self.ticket_data: Dict[str, TicketSets] = load_all_tickets()
        self.winning_data: Dict[str, Winning] = load_all_winnings()

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout()

        # Холст для графика
        self.figure = plt.Figure(figsize=(12, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(400, 300)  # минимальный размер
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        main_layout.addWidget(self.canvas, stretch=1)

        # Метка для показа значений при наведении
        self.lbl_hover = QLabel("Наведите на график, чтобы увидеть детали")
        self.lbl_hover.setStyleSheet("font-size: 13px; font-weight: bold; color: green; padding: 5px;")
        main_layout.addWidget(self.lbl_hover)

        # --- Нижние кнопки ---
        bottom_layout = QHBoxLayout()

        # Кнопка обновления (если данные могли измениться)
        btn_refresh = Button("Обновить график", fixed_width=180)
        btn_refresh.clicked.connect(self.refresh_chart)  # type: ignore
        bottom_layout.addWidget(btn_refresh)

        bottom_layout.addStretch()

        btn_back = Button("Назад", fixed_width=180)
        btn_back.clicked.connect(self.open_main_window)
        bottom_layout.addWidget(btn_back)

        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

        # Построить график при открытии окна
        self.refresh_chart()

    def refresh_chart(self):
        """Пересчитывает данные и перерисовывает график на существующем Figure."""
        dates_sorted, wins_m, wins_b = self._prepare_data()

        if not dates_sorted:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, "Нет данных для отображения",
                    transform=ax.transAxes, ha='center', va='center')
            ax.axis('off')
            self.canvas.draw()
            return

        # Очищаем фигуру и рисуем заново
        self.figure.clear()
        ax1 = self.figure.add_subplot(111)

        color_m = '#2e7d32'
        ax1.plot(dates_sorted, wins_m, color=color_m, marker='o', linewidth=2,
                 markersize=6, label='Выигрыш (м.)', zorder=3)
        ax1.fill_between(dates_sorted, wins_m, alpha=0.1, color=color_m, zorder=2)
        ax1.set_xlabel('Дата розыгрыша', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Выигрыш в морковках', fontsize=12, color=color_m, fontweight='bold')
        ax1.tick_params(axis='y', labelcolor=color_m)
        ax1.set_ylim(bottom=0)

        ax2 = ax1.twinx()
        color_b = '#1565c0'
        x_pos = date2num(dates_sorted)
        ax2.bar(x_pos, wins_b, width=0.4, color=color_b, alpha=0.7,
                label='Выигрыш (б.)', zorder=1, edgecolor=color_b, linewidth=1.5)
        ax2.set_ylabel('Выигрыш в баллах', fontsize=12, color=color_b, fontweight='bold')
        ax2.tick_params(axis='y', labelcolor=color_b)
        ax2.set_ylim(0, max(wins_b) * 1.2 if max(wins_b) > 0 else 100)

        ax1.xaxis.set_major_formatter(DateFormatter('%d.%m.%y'))
        for label in ax1.get_xticklabels():
            label.set_rotation(30)
            # label.set_ha('right')

        ax1.grid(True, alpha=0.3, linestyle='--')

        # Подписи значений
        for d, b_val in zip(dates_sorted, wins_b):
            if b_val > 0:
                ax2.annotate(str(b_val), (date2num(d), b_val),
                             textcoords="offset points", xytext=(0, 5),
                             ha='center', fontsize=9, color=color_b)

        ax1.set_title('Выигрыши по розыгрышам', fontsize=14, fontweight='bold', pad=15)

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)

        self.figure.tight_layout()
        self.canvas.draw()  # перерисовка

    def _prepare_data(self):
        """Возвращает три списка: даты (datetime), выигрыши м., выигрыши б."""
        dates_sorted = []
        wins_m = []
        wins_b = []

        for date_str in sorted(self.results_data.keys(),
                               key=lambda d: dt.strptime(d, '%d.%m.%y')):
            result = self.results_data[date_str]
            ticket_data = self.ticket_data.get(date_str)
            if not ticket_data:
                continue

            win_set = self.winning_data.get(ticket_data.win_set, {})
            won_m, won_b, spent = result.calculate_winnings_for_tickets(win_set, ticket_data)

            dates_sorted.append(dt.strptime(date_str, '%d.%m.%y'))
            wins_m.append(won_m)
            wins_b.append(won_b)

        return dates_sorted, wins_m, wins_b

    def on_motion(self, event):
        if event.inaxes is None:
            self.lbl_hover.setText("Наведите на график, чтобы увидеть детали")
            return

        # Получаем данные, которые сейчас на графике
        dates_sorted, wins_m, wins_b = self._prepare_data()
        if not dates_sorted:
            return

        xdata = event.xdata
        ydata = event.ydata

        # Ищем ближайшую дату (по оси X)
        # xdata — это float (date2num), сравниваем с date2num от дат
        xvals = [date2num(d) for d in dates_sorted]

        best_idx = min(range(len(xvals)), key=lambda i: abs(xvals[i] - xdata))
        date_str = dates_sorted[best_idx].strftime('%d.%m.%y')
        m_val = wins_m[best_idx]
        b_val = wins_b[best_idx]

        text = f"Дата: {date_str}"
        text += f" | Морковки: {m_val} 🥕" if m_val else ''
        text += f" | Баллы: {b_val} 💵" if b_val else ''
        self.lbl_hover.setText(text)

    def open_main_window(self):
        self.window = WelcomeWindow()
        self.window.show()
        self.close()


def change_style(widget, parameter: str, value: str):
    style = widget.styleSheet()
    pattern = r'(?<!-)\b' + re.escape(parameter) + r'\b(\s*:\s*)[^;]+'
    if re.search(pattern, style):
        widget.setStyleSheet(re.sub(pattern, parameter + r'\1' + value, style))


# Unhandled exception interceptor
def excepthook(exc_type, exc_value, tb):
    import traceback
    traceback.print_exception(exc_type, exc_value, tb)
    QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # app.setStyle('Fusion')
    window = WelcomeWindow()
    window.show()
    sys.excepthook = excepthook
    sys.exit(app.exec())

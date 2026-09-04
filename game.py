# TODO:
#   - InputWindow: при выходе или смене даты сравнивать введенные данные с сохраненными и если отличается, то предложить сохранить
#   - InputWindow: при сохранении дата и набор не должны сбрасываться
#   - ResultWindow: при выходе или смене даты сравнивать введенные данные с сохраненными и если отличается, то предложить сохранить
#   - ResultWindow: сортировка кнопок также как win_set

import sys, json, random, os, re
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, asdict, field

from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QVBoxLayout, QMessageBox, QFrame, QGridLayout,
                             QWidget, QLabel, QPushButton, QComboBox, QRadioButton, QScrollArea)
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtCore import QSize, pyqtSignal

VERSION = '1.04 (2026.09)'
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "tickets.json")
RESULTS_FILE = os.path.join(DATA_DIR, "results.json")
WINNINGS_FILE = os.path.join(DATA_DIR, "win_sets.json")
CARD1_SIZE = 35
CARD2_SIZE = 54

COLORS = [
    QColor("#9ac87d"),  # 1 — светло-зелёный
    QColor("#00b0f0"),  # 2 — голубой #dcfdfd
    QColor("yellow"),  # 3 — светло-жёлтый #fff9c4
    QColor("#a0a0a0"),  # 4 — светло-серый
    QColor("#ffaaaa"),  # 5 — светло-красный
]
RESULT_COLOR = QColor("#FFC000")

def is_valid_date(date_str: str) -> bool:
    """Проверяет, что строка в формате dd.mm.yy и является реальной датой."""
    if not date_str:
        return False
    try:
        datetime.strptime(date_str, "%d.%m.%y")
        return True
    except ValueError:
        return False


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_all_data() -> Dict[str, 'TicketSets']:
    ensure_data_dir()
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {d["date"]: TicketSets.from_dict(d) for d in data}
    except Exception:
        return {}


def save_all_data(data: Dict[str, 'TicketSets']):
    ensure_data_dir()
    serialized = [d.to_dict() for d in data.values()]
    with open(DATA_FILE, "w", encoding="utf-8") as f:
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


def save_all_winnings(winnings: List["Winning"]):
    ensure_data_dir()
    serialized = [w.to_dict() for w in winnings]
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
    sets: List[List[Ticket]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "TicketSets":
        sets = []
        for s in d.get("sets", []):
            sets.append([Ticket(**t) for t in s])
        return cls(date=d["date"], sets=sets)

    def to_dict(self) -> dict:
        sets_serialized = []
        for s in self.sets:
            sets_serialized.append([asdict(t) for t in s])
        return {"date": self.date, "sets": sets_serialized}

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
        2. Есть хотя бы один набор.
        3. Все наборы кроме последнего — полные (5 валидных билетов).
        4. В последнем наборе есть хотя бы один валидный билет.
        """
        if not is_valid_date(self.date):
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


@dataclass
class Winning:
    name: str
    cost: int
    sets: Dict[Tuple[int, int], list]

    @classmethod
    def from_dict(cls, d: dict) -> "Winning":
        raw_sets = d.get("sets", {})
        parsed_sets = {}
        for k, v in raw_sets.items():
            parsed_sets[cls._parse_key(k)] = v
        return cls(name=d["name"], cost=d["cost"], sets=parsed_sets)

    def to_dict(self) -> dict:
        raw_sets = {}
        for k, v in self.sets.items():
            raw_sets[self._format_key(k)] = v
        return {"name": self.name, "cost": self.cost, "sets": raw_sets}

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
    def __init__(self, fixed_width=0, fixed_height=30, editable=False):
        super().__init__()
        self.setStyleSheet('color: #203764; font-size: 16px')
        self.setMaxVisibleItems(10)
        self.setEditable(editable)
        if fixed_width:
            self.setFixedWidth(fixed_width)
        if fixed_height:
            self.setFixedHeight(fixed_height)


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
        super().__init__('Carrots', height=220)
        self._init_ui()

    def _init_ui(self):
        button_input = Button('Билеты', fixed_height=50)
        button_input.clicked.connect(self.open_input_data_window)
        button_results = Button('Результаты', fixed_height=50)
        button_results.clicked.connect(self.open_results_window)
        button_about = Button('О программе', fixed_height=50)
        button_about.clicked.connect(self.on_click_about)

        main_v_layout = QVBoxLayout()
        main_v_layout.addWidget(button_input)
        main_v_layout.addWidget(button_results)
        main_v_layout.addWidget(button_about)
        self.setLayout(main_v_layout)

    def open_input_data_window(self):
        self.window = InputWindow()
        self.window.show()
        self.close()

    def open_results_window(self):
        self.window = ResultWindow('')
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
            btn.clicked.connect(lambda _, idx=i: self.cell_clicked.emit(idx))
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


class InputWindow(Window):
    def __init__(self):
        super().__init__('Билеты', width=800, height=600)
        self.all_data: Dict[str, TicketSets] = load_all_data()
        self.current_date: Optional[str] = None
        self.selected_ticket_index = 0
        self.current_set_index = 0
        self.first_time = True

        self.all_results: Dict[str, Result] = load_all_results()
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
        self.date_combo = ComboList(fixed_width=100, editable=True)
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
        set_row.addWidget(self.combo_set)
        left_layout.addLayout(set_row)

        left_layout.addSpacing(12)

        # 3. Радиокнопки выбора билета
        self.color_buttons: List[QRadioButton] = []
        for i, color in enumerate(COLORS):
            rb = QRadioButton(f'Билет {i + 1} (0/7 + 0)')
            rb.setAutoExclusive(True)
            rb.setStyleSheet(
                f'background-color: {color.name()}; padding: 6px; '
                f'color: #203764; border: 1px solid #888; font-size: 16px; font-weight: bold; '
            )
            rb.clicked.connect(lambda _, idx=i: self._set_color(idx))
            self.color_buttons.append(rb)
            left_layout.addWidget(rb)
        self.color_buttons[0].setChecked(True)

        left_layout.addSpacing(12)

        # 4. Кнопки управления
        self.btn_generate = Button("Генерировать")
        self.btn_generate.clicked.connect(self.on_generate)

        self.btn_generate_all = Button("Генерировать все")
        self.btn_generate_all.clicked.connect(self.on_generate_all)

        self.btn_add_set = Button("Добавить набор")
        self.btn_add_set.clicked.connect(self.on_add_set)

        self.btn_remove_set = Button("Удалить набор")
        self.btn_remove_set.clicked.connect(self.on_remove_set)

        self.btn_save_set = Button("Сохранить")
        self.btn_save_set.clicked.connect(self.on_save)

        self.btn_back = Button("Назад")
        self.btn_back.clicked.connect(self.open_main_window)

        left_layout.addWidget(self.btn_generate)
        left_layout.addWidget(self.btn_generate_all)
        left_layout.addWidget(self.btn_add_set)
        left_layout.addWidget(self.btn_remove_set)
        left_layout.addWidget(self.btn_save_set)
        left_layout.addStretch()
        left_layout.addWidget(self.btn_back)

        # === Правая панель ===
        right = QWidget()
        right_layout = QVBoxLayout()
        right.setLayout(right_layout)

        # Карточки
        self.card1 = CardWidget(rows=4, cols=9, active=CARD1_SIZE)
        self.card1.cell_clicked.connect(self.on_card1_click)
        right_layout.addWidget(self.card1)

        right_layout.addStretch()

        self.card2 = CardWidget(rows=6, cols=9, active=CARD2_SIZE)
        self.card2.cell_clicked.connect(self.on_card2_click)
        right_layout.addWidget(self.card2)

        main_layout.addWidget(left, stretch=1)
        main_layout.addWidget(right, stretch=4)
        self.setLayout(main_layout)

    # ── Логика переключения даты и набора ──

    def _refresh_dates(self):
        dates = sorted(self.all_data.keys(), reverse=True, key=lambda d: datetime.strptime(d, '%d.%m.%y'))
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
        self.current_date = text.strip() if text else None
        self._load_current_context()

    def on_remove_date(self):
        if not self.current_date or self.current_date not in self.all_data:
            return
        reply = QMessageBox.question(self, 'Удаление билетов',
                                     f'Вы действительно хотите удалить все билеты\nза {self.current_date}?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        del self.all_data[self.current_date]
        save_all_data(self.all_data)

        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        self.date_combo.addItems(sorted(self.all_results.keys(), reverse=True, key=lambda d: datetime.strptime(d, '%d.%m.%y')))
        self.date_combo.blockSignals(False)
        self.date_combo.setCurrentText('')

    def _load_current_context(self):
        """Загружает данные для выбранной даты и набора"""
        self.combo_set.clear()

        if self.combo_set.count() == 0:
            self.combo_set.addItem(f"Набор 1")

        if not self.current_date or self.current_date not in self.all_data:
            # Пустая дата
            self._clear_cards()
            self._update_radio_buttons()
            return

        data = self.all_data[self.current_date]

        # Заполняем комбобокс наборами
        if data.sets:
            for i in range(1, len(data.sets)):
                self.combo_set.addItem(f"Набор {i + 1}")

        if len(data.sets) > 0:
            self.combo_set.setCurrentIndex(0)
            self._apply_set_data(0)
        else:
            self._clear_cards()

        self._update_radio_buttons()

    def _on_set_changed(self, index: int):
        if self.current_date and self.current_date in self.all_data:
            self.current_set_index = index
            self._apply_set_data(index)
            self._update_radio_buttons()

    def _apply_set_data(self, set_idx: int):
        data = self.all_data[self.current_date]
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

        if self.current_date not in self.all_data:
            self.all_data[self.current_date] = TicketSets(date=self.current_date)

        self.all_data[self.current_date].add_empty_set()

        # Перезагружаем контекст, чтобы обновить комбо и выбрать новый набор
        self._load_current_context()
        last_idx = len(self.all_data[self.current_date].sets) - 1
        self.combo_set.setCurrentIndex(last_idx)
        self.current_set_index = last_idx

    def on_remove_set(self):
        if not self.current_date or self.current_date not in self.all_data:
            return

        data = self.all_data[self.current_date]
        count = len(data.sets)

        if count == 0:
            return

        if count == 1:
            # Если один набор - просто очищаем его и оставляем пустым
            data.sets[0] = []
            self._clear_cards()
            self._update_radio_buttons()
            return

        # Удаляем текущий набор
        data.remove_set(self.current_set_index)

        # Обновляем UI
        new_index = min(self.current_set_index, len(data.sets) - 1)
        self._load_current_context()  # Полная перезагрузка комбо
        self.combo_set.setCurrentIndex(new_index)
        self.current_set_index = new_index

    # ── Вспомогательные методы UI ──

    def calc_top_nums(self):
        if len(self.all_results) == 0:
            return None
        dates = sorted(self.all_results.keys(), reverse=True, key=lambda d: datetime.strptime(d, '%d.%m.%y'))
        nums = [self.all_results[d].second_card_selected for d in dates
                if self.all_results[d].second_card_selected is not None][:30]
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
                self.current_date not in self.all_data or
                len(self.all_data[self.current_date].sets) < 2):
            return
        for idx in range(len(self.all_data[self.current_date].sets)):
            if idx != self.current_set_index:
                for num in [t.second_card_selected for t in self.all_data[self.current_date].sets[idx]]:
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
            text = f"Билет {ticket_idx+1} ({c1}/7 + {c2})"
            self.color_buttons[ticket_idx].setText(text)
            color = 'green' if c1 + c2 == 8 else 'red'
            change_style(self.color_buttons[ticket_idx], 'color', color)

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

    def _check_validity(self) -> bool:
        if not self.current_date:
            QMessageBox.warning(self, "Ошибка", "Укажите дату!")
            return False
        if not is_valid_date(self.current_date):
            QMessageBox.warning(self, "Ошибка", "Неверный формат даты! Используйте dd.mm.yy")
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
        for idx in range(len(self.all_data[self.current_date].sets)):
            if idx != self.current_set_index:
                second_card_selected = [t.second_card_selected for t in self.all_data[self.current_date].sets[idx]]
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

    def on_generate_all(self):
        if not self._check_validity():
            return
        self._clear_cards()
        self._sync_to_data()
        for i in range(1, 6):
            self._generator(i)

    def _sync_to_data(self):
        """Записывает текущее состояние карточек в self.all_data"""
        if not self.current_date:
            return

        if self.current_date not in self.all_data:
            self.all_data[self.current_date] = TicketSets(date=self.current_date)

        data = self.all_data[self.current_date]

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

    def on_save(self):
        if not self._check_validity():
            return

        data = self.all_data[self.current_date]

        if not data.is_valid():
            errors = []
            if not is_valid_date(data.date):
                errors.append("Неверный формат даты.")
            for i, s in enumerate(data.sets[:-1]):
                if not data.is_set_full(s):
                    errors.append(f"Набор {i+1} заполнен не полностью (нужно 5 валидных билетов).")
            if not any(t.is_valid() for t in data.sets[-1]):
                errors.append("В последнем наборе нет ни одного валидного билета, заполненного 7+1.")
            msg = "\n".join(errors)
            QMessageBox.warning(self, "Ошибка валидации", msg)
            return

        save_all_data(self.all_data)
        self._refresh_dates()
        # Восстанавливаем выбранную дату и набор
        self.date_combo.setCurrentText(self.current_date)
        self.combo_set.setCurrentIndex(self.current_set_index)
        QMessageBox.information(self, 'Успешно', f'Данные сохранены в {DATA_FILE}')

    def open_main_window(self):
        self.window = WelcomeWindow()
        self.window.show()
        self.close()


class ResultWindow(Window):
    def __init__(self, date: str = ''):
        super().__init__('Результаты', width=800, height=600)
        self.all_results: Dict[str, Result] = load_all_results()
        self.ticket_data: Dict[str, TicketSets] = load_all_data()
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
        self.date_combo = ComboList(fixed_width=105, editable=True)
        dates = sorted(self.all_results.keys(), reverse=True, key=lambda d: datetime.strptime(d, '%d.%m.%y'))
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

        # Тип выигрыша
        win_row = QHBoxLayout()
        win_row.addWidget(Label("Тип выигрыша:"))
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
        self.card1.cell_clicked.connect(self.on_card1_click)
        right_layout.addWidget(self.card1)

        right_layout.addStretch()

        self.selected_label = Label('')
        right_layout.addWidget(self.selected_label)

        self.result_label = Label('')
        right_layout.addWidget(self.result_label)

        right_layout.addStretch()

        self.card2 = CardWidget(rows=6, cols=9, active=CARD2_SIZE)
        self.card2.cell_clicked.connect(self.on_card2_click)
        right_layout.addWidget(self.card2)

        main_layout.addWidget(left, stretch=1)
        main_layout.addWidget(right, stretch=4)
        self.setLayout(main_layout)

    # ── Переключение даты ──

    def _on_date_changed(self, text: str):
        self.current_date = text.strip() if text else None
        self._load_result()
        if self.current_date and self.current_date in self.all_results:
            self.win_combo.setCurrentText(self.all_results[self.current_date].win_set)
        self._update_labels()

    def on_remove_date(self):
        if not self.current_date or self.current_date not in self.all_results:
            return
        reply = QMessageBox.question(self, 'Удаление результата',
                                     f'Вы действительно хотите удалить результат\nза {self.current_date}?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        del self.all_results[self.current_date]
        save_all_results(self.all_results)

        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        self.date_combo.addItems(sorted(self.all_results.keys(), reverse=True, key=lambda d: datetime.strptime(d, '%d.%m.%y')))
        self.date_combo.blockSignals(False)
        self.date_combo.setCurrentText('')

    def _on_win_set_changed(self):
        self._rebuild_buttons()

    def _load_result(self):
        self.result_first = set()
        self.result_second = None
        self._clear_cards()
        self._clear_outlines()
        self._clear_buttons()

        if not self.current_date or self.current_date not in self.all_results:
            return

        result = self.all_results[self.current_date]
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

        for set_idx, ticket_set in enumerate(ts.sets):
            for ticket in ticket_set:
                # Считаем совпадения
                ticket_first = set(ticket.first_card_selected)
                x = len(ticket_first & result_first_set)
                y = 1 if (ticket.second_card_selected is not None and
                          ticket.second_card_selected == result_second) else 0

                # Условие: >=2 в первой ИЛИ совпадение во второй
                if x >= 2 or y >= 1:
                    color = COLORS[ticket.ticket - 1]
                    win_result = self.winning_data[self.win_combo.currentText()].sets[(x, y)]
                    text = f"Набор {set_idx + 1}/билет {ticket.ticket}: {x}+{y}={win_result[0]:,d}{win_result[1]}"
                    btn = Button(text)
                    btn.setStyleSheet(
                        f"font-size: 14px; font-weight: bold; color: #203764; "
                        f"border: 1px solid #888; border-radius: 4px; "
                        f"background-color: {color.name()}; padding: 6px;"
                    )
                    btn.clicked.connect(lambda _, t=ticket: self._show_ticket_outline(t))
                    # Вставляем перед stretch
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
        ts = self.ticket_data[self.current_date]

        valid_count = 0
        won_m = 0   # сумма в 'м.'
        won_b = 0   # сумма в 'б.'

        result_first_set = self.result_first
        result_second = self.result_second

        for ticket_set in ts.sets:
            for ticket in ticket_set:
                if not ticket.is_valid():
                    continue
                valid_count += 1

                x = len(set(ticket.first_card_selected) & result_first_set)
                y = 1 if (ticket.second_card_selected is not None and
                          ticket.second_card_selected == result_second) else 0

                key = (x, y)
                if key in win_data.sets:
                    amount, kind = win_data.sets[key]
                    if kind == 'м.':
                        won_m += amount
                    elif kind == 'б.':
                        won_b += amount

        spent = valid_count * win_data.cost
        won_text = f'{won_m:,d} м., ' if won_m else ''
        won_text += f'{won_b:,d} б.' if won_b else ''
        if won_m or won_b:
            self.result_label.setText(f'Потрачено: {spent:,d} м., выиграно {won_text.strip(", ")}')
        else:
            self.result_label.setText(f'Потрачено: {spent:,d} м.')

    # ── Сохранение ──

    def on_save(self):
        error_text = []
        if not self.current_date:
            error_text = ["Укажите дату!"]
        if self.current_date and not is_valid_date(self.current_date):
            error_text.append("Неверный формат даты! Используйте dd.mm.yy")
        if len(self.result_first) < 7:
            error_text.append('В первой карточке должно быть выделено 7 ячеек!')
        if self.result_second is None:
            error_text.append('Укажите ячейку во второй карточке!')
        if error_text:
            QMessageBox.warning(self, "Ошибка", '\n'.join(error_text))
            return

        result = Result(
            date=self.current_date,
            win_set=self.win_combo.currentText(),
            first_card_selected=sorted(self.result_first),
            second_card_selected=self.result_second
        )
        self.all_results[self.current_date] = result
        save_all_results(self.all_results)

        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        self.date_combo.addItems(sorted(self.all_results.keys(), reverse=True, key=lambda d: datetime.strptime(d, '%d.%m.%y')))
        self.date_combo.setCurrentText(self.current_date)
        self.date_combo.blockSignals(False)

        QMessageBox.information(self, "Успех", f"Результат сохранён в {RESULTS_FILE}")

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

# TODO:
#   - InputWindow: при выходе или смене даты сравнивать введенные данные с сохраненными и если отличается, то предложить сохранить
#   - InputWindow: кнопка удаления данных за дату

import sys, json, random, os, re
from datetime import datetime
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict, field

from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QVBoxLayout, QMessageBox, QFrame, QGridLayout,
                             QWidget, QLabel, QPushButton, QComboBox, QRadioButton)
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtCore import QSize, pyqtSignal

VERSION = '1.01 (2026.09)'
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "tickets.json")
CARD1_SIZE = 35
CARD2_SIZE = 54


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


class Label(QLabel):
    def __init__(self, text: str, fixed_width=0, fixed_height=30):
        super().__init__(text)
        self.setStyleSheet('color: #203764; font-size: 16px; font-weight: bold')
        if fixed_width:
            self.setFixedWidth(fixed_width)
        if fixed_height:
            self.setFixedHeight(fixed_height)


class Button(QPushButton):
    def __init__(self, text: str, fixed_width=0, fixed_height=40, icon_size=24):
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
        button_input = Button('Ввод', fixed_height=50)
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
            # Скрываем лишние ячейки, если их больше чем active
            if i >= active:
                btn.setVisible(False)

    def set_cell_color(self, idx: int, color: Optional[QColor]):
        if idx < 0 or idx >= self.active:
            return
        btn = self.buttons[idx]
        if color is None:
            change_style(btn, 'background-color', 'white')
        else:
            change_style(btn, 'background-color', color.name())


class InputWindow(Window):
    COLORS = [
        QColor("#a8e6cf"),  # светло-зелёный
        QColor("#dcfdfd"),  # голубой
        QColor("#fff9c4"),  # светло-жёлтый
        QColor("#ffcccc"),  # светло-красный
        QColor("#a0a0a0"),  # светло-серый
    ]

    def __init__(self):
        super().__init__('Ввод данных', width=800, height=600)
        self.all_data: Dict[str, TicketSets] = load_all_data()
        self.current_date: Optional[str] = None
        self.selected_ticket_index = 0
        self.current_set_index = 0

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
        date_row.addWidget(Label("Дата:"))
        self.date_combo = ComboList(fixed_width=100, editable=True)
        self.date_combo.currentTextChanged.connect(self._on_date_changed)
        date_row.addWidget(self.date_combo)
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
        for i, color in enumerate(self.COLORS):
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
        dates = sorted(self.all_data.keys(), reverse=True)
        self.date_combo.blockSignals(True)
        self.date_combo.clear()
        self.date_combo.addItems(dates)
        if dates:
            self.date_combo.setCurrentIndex(0)
            self.current_date = dates[0]
        else:
            self.current_date = None
        self.date_combo.blockSignals(False)
        self._load_current_context()

    def _on_date_changed(self, text: str):
        self.current_date = text.strip() if text else None
        self._load_current_context()

    def _load_current_context(self):
        """Загружает данные для выбранной даты и набора"""
        self.current_set_index = 0
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
            self.card1.set_cell_color(i, self.COLORS[v - 1] if v > 0 else None)
        for i in range(CARD2_SIZE):
            v = self.second_card[i]
            self.card2.set_cell_color(i, self.COLORS[v - 1] if v > 0 else None)

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
        if not self._check_validity():
            return

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
        self.second_card[random.choice(free2)] = ticket

        self._render_cards()
        self._update_radio_buttons()
        self._sync_to_data()

    def on_generate(self):
        self._generator(self.selected_ticket_index + 1)

    def on_generate_all(self):
        self._clear_cards()
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
    pass


def change_style(widget, parameter: str, value: str):
    style = widget.styleSheet()
    pattern = rf'([^-]\b{parameter}:[ ]?)([#]?\b\w+\b)'
    if re.search(pattern, style):
        widget.setStyleSheet(re.sub(pattern, rf'\1{value}', style))

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

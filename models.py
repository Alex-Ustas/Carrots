from funcs import *
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Tuple


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

    def get_current_tickets(self, index: int) -> List[Ticket]:
        if 0 <= index < len(self.sets):
            return self.sets[index]
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
        1. Корректная дата в формате dd.mm.yy.
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
    date: str  # dd.mm.yy
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

    def calculate_winnings_for_tickets(self, winning_scheme: 'Winning', tickets: TicketSets) -> Tuple[int, int, int]:
        """
        Рассчитывает суммарный выигрыш (в 'м.' и 'б.') и затраты
        для всех валидных билетов из tickets по текущему результату.
        Возвращает: (won_m, won_b, spent).
        """
        valid_count = 0
        won_m = 0
        won_b = 0

        for ticket_set in tickets.sets:
            for ticket in ticket_set:
                if not ticket.is_valid():
                    continue

                valid_count += 1

                x = len(set(ticket.first_card_selected) & set(self.first_card_selected))
                y = 1 if (ticket.second_card_selected is not None
                          and ticket.second_card_selected == self.second_card_selected) else 0

                prize = winning_scheme.sets.get((x, y))
                if prize:
                    amount, kind = prize
                    if kind == 'м.':
                        won_m += amount
                    elif kind == 'б.':
                        won_b += amount

        spent = valid_count * tickets.cost
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
        try:
            parts = list(map(int, key.split("_")))
            return parts[0], parts[1]
        except (ValueError, IndexError):
            return 0, 0

    @staticmethod
    def _format_key(key: Tuple[int, int]) -> str:
        return f"{key[0]}_{key[1]}"

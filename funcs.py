from typing import Tuple
from datetime import datetime as dt

DATE_FORMAT = "%d.%m.%y"


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
        dt.strptime(date_str, DATE_FORMAT)
        return True
    except ValueError:
        return False

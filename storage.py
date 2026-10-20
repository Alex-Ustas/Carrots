from models import TicketSets, Result, Winning

from typing import List, Dict, TypeVar, Callable
from pathlib import Path
import json

T = TypeVar("T")
DATA_DIR = Path("data")
TICKETS_FILE = DATA_DIR / "tickets.json"
RESULTS_FILE = DATA_DIR / "results.json"
WINNINGS_FILE = DATA_DIR / "win_sets.json"


# Общий шаблон загрузки списка объектов и построения словаря по ключу
def _load_list_to_dict(
        path: Path, item_from_dict: Callable[[dict], T], key_extractor: Callable[[dict], str]
) -> Dict[str, T]:
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {}
    except OSError:
        return {}

    result: Dict[str, T] = {}
    for item_raw in data:
        try:
            key = key_extractor(item_raw)
            obj = item_from_dict(item_raw)
            result[key] = obj
        except (KeyError, TypeError, ValueError):
            continue
    return result


# Общий шаблон сохранения словаря как списка объектов
def _save_dict_as_list(path: Path, data: Dict[str, T], item_to_dict: Callable[[T], dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    serialized: List[dict] = [item_to_dict(v) for v in data.values()]
    with path.open("w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)


def load_all_tickets() -> Dict[str, TicketSets]:
    return _load_list_to_dict(TICKETS_FILE, item_from_dict=TicketSets.from_dict, key_extractor=lambda d: d["date"])


def load_all_results() -> Dict[str, Result]:
    return _load_list_to_dict(RESULTS_FILE, item_from_dict=Result.from_dict, key_extractor=lambda r: r["date"])


def load_all_winnings() -> Dict[str, Winning]:
    return _load_list_to_dict(WINNINGS_FILE, item_from_dict=Winning.from_dict, key_extractor=lambda w: w["name"])


def save_all_tickets(data: Dict[str, TicketSets]) -> None:
    _save_dict_as_list(TICKETS_FILE, data, item_to_dict=lambda ts: ts.to_dict())


def save_all_results(data: Dict[str, Result]) -> None:
    _save_dict_as_list(RESULTS_FILE, data, item_to_dict=lambda r: r.to_dict())


def save_all_winnings(data: Dict[str, Winning]) -> None:
    _save_dict_as_list(WINNINGS_FILE, data, item_to_dict=lambda w: w.to_dict())

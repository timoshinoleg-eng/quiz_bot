from types import SimpleNamespace

from scripts.content.audit import fuzzy_duplicate_count


def question(text: str, answer: str, options: list[str]):
    return SimpleNamespace(text=text, correct_answer=answer, wrong_answers=options)


def test_fuzzy_audit_blocks_reworded_copy_of_same_fact():
    rows = [
        question("Что это: устройство для ввода текста в компьютер?", "клавиатура", ["мышь", "монитор", "принтер"]),
        question("Что это: устройство для ввода текста в компьютере?", "клавиатура", ["мышь", "монитор", "принтер"]),
    ]
    assert fuzzy_duplicate_count(rows) == 1


def test_fuzzy_audit_allows_similar_templates_with_different_answers():
    rows = [
        question("Сколько будет 10 × 5?", "50", ["40", "45", "55"]),
        question("Сколько будет 17 × 5?", "85", ["75", "80", "90"]),
    ]
    assert fuzzy_duplicate_count(rows) == 0

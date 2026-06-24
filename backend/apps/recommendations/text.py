import re
import unicodedata


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalize_text(value):
    value = str(value or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", value)
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return without_marks.replace("đ", "d")


def tokenize(value):
    return TOKEN_PATTERN.findall(normalize_text(value))


def contains_any(value, phrases):
    normalized = normalize_text(value)
    return any(normalize_text(phrase) in normalized for phrase in phrases)

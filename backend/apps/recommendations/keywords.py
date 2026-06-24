from dataclasses import dataclass, field
from decimal import Decimal
import re

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import models

from .text import normalize_text, tokenize


AMENITY_SYNONYMS = {
    "wifi": ["wifi", "internet", "mang", "net"],
    "parking": ["giu xe", "cho de xe", "de xe", "xe may", "bai xe"],
    "air_conditioner": ["may lanh", "dieu hoa", "aircon", "ac"],
    "private_bathroom": ["wc rieng", "ve sinh rieng", "toilet rieng", "nha tam rieng"],
    "kitchen": ["bep", "nau an", "tu nau", "khu bep"],
    "security": ["an ninh", "bao ve", "camera", "khoa van tay", "gio giac tu do"],
    "furnished": ["noi that", "giuong", "tu do", "ban hoc", "co san do"],
    "window": ["cua so", "thoang", "ban cong", "anh sang"],
}

INTENT_SYNONYMS = {
    "cheap": ["re", "gia re", "sinh vien", "tiet kiem", "binh dan"],
    "quiet": ["yen tinh", "it on", "khong on", "hoc tap"],
    "spacious": ["rong", "rong rai", "dien tich lon", "thoai mai"],
    "near_school": ["gan truong", "di bo", "gan dh", "gan dai hoc", "sat truong"],
    "near_center": ["gan trung tam", "quan 1", "trung tam", "cho", "sieu thi", "tttm"],
    "near_park": ["gan cong vien", "cong vien", "cay xanh"],
    "near_bus": ["gan tram bus", "gan xe bus", "ben xe bus", "tram xe bus", "bus"],
    "near_hospital": ["gan benh vien", "benh vien", "phong kham"],
    "near_mall": ["gan trung tam thuong mai", "trung tam thuong mai", "tttm", "mall"],
    "female": ["nu", "ban nu", "o ghep nu"],
    "male": ["nam", "ban nam", "o ghep nam"],
}

STOPWORDS = {
    "phong",
    "tro",
    "can",
    "tim",
    "cho",
    "thue",
    "o",
    "ghep",
    "gan",
    "khu",
    "vuc",
    "co",
    "va",
    "voi",
}


@dataclass
class KeywordIntent:
    raw_query: str
    normalized_query: str
    tokens: list[str]
    matched_intents: list[str] = field(default_factory=list)
    amenity_codes: list[str] = field(default_factory=list)
    searchable_terms: list[str] = field(default_factory=list)
    unknown_terms: list[str] = field(default_factory=list)
    fallback_used: bool = False

    @property
    def has_signal(self):
        return bool(self.matched_intents or self.amenity_codes or self.searchable_terms)

    def as_dict(self):
        return {
            "raw_query": self.raw_query,
            "matched_intents": self.matched_intents,
            "amenity_codes": self.amenity_codes,
            "searchable_terms": self.searchable_terms,
            "unknown_terms": self.unknown_terms,
            "fallback_used": self.fallback_used,
        }


def _match_synonyms(normalized_query, synonym_map):
    matches = []
    for key, phrases in synonym_map.items():
        if any(normalize_text(phrase) in normalized_query for phrase in phrases):
            matches.append(key)
    return matches


def extract_keyword_intent(query):
    normalized_query = normalize_text(query)
    tokens = tokenize(query)
    matched_intents = _match_synonyms(normalized_query, INTENT_SYNONYMS)
    amenity_codes = _match_synonyms(normalized_query, AMENITY_SYNONYMS)
    searchable_terms = [token for token in tokens if len(token) >= 3 and token not in STOPWORDS]
    known_parts = set()
    for phrase_map in (INTENT_SYNONYMS, AMENITY_SYNONYMS):
        for phrases in phrase_map.values():
            for phrase in phrases:
                known_parts.update(tokenize(phrase))
    unknown_terms = [
        token
        for token in searchable_terms
        if token not in known_parts and token not in matched_intents and token not in amenity_codes
    ]
    return KeywordIntent(
        raw_query=query or "",
        normalized_query=normalized_query,
        tokens=tokens,
        matched_intents=matched_intents,
        amenity_codes=amenity_codes,
        searchable_terms=searchable_terms,
        unknown_terms=unknown_terms,
    )


def extract_price_ceiling(query):
    normalized = normalize_text(query)
    match = re.search(r"(?:duoi|toi da|max)\s*(\d+(?:[,.]\d+)?)\s*(trieu|tr|k|nghin)?", normalized)
    if not match:
        return None
    number = Decimal(match.group(1).replace(",", "."))
    unit = match.group(2)
    if unit in {"trieu", "tr"}:
        return number * Decimal("1000000")
    if unit in {"k", "nghin"}:
        return number * Decimal("1000")
    return number


@dataclass
class SearchResult:
    queryset: object
    intent: KeywordIntent


def _apply_amenity_filters(queryset, amenity_codes):
    for code in amenity_codes:
        phrases = AMENITY_SYNONYMS.get(code, [code])
        query = models.Q(amenities__code__icontains=code)
        for phrase in phrases:
            query |= models.Q(amenities__name__icontains=phrase)
        queryset = queryset.filter(query)
    return queryset.distinct()


def apply_room_keyword_search(queryset, query):
    intent = extract_keyword_intent(query)
    if not intent.has_signal:
        intent.fallback_used = bool(query)
        return SearchResult(queryset.order_by("-created_at"), intent)

    narrowed = queryset
    if intent.amenity_codes:
        narrowed = _apply_amenity_filters(narrowed, intent.amenity_codes)
    ceiling = extract_price_ceiling(query)
    if ceiling is not None:
        narrowed = narrowed.filter(price__lte=ceiling)
    if "female" in intent.matched_intents:
        narrowed = narrowed.filter(gender_policy__in=["any", "female"])
    if "male" in intent.matched_intents:
        narrowed = narrowed.filter(gender_policy__in=["any", "male"])
    if "spacious" in intent.matched_intents:
        narrowed = narrowed.filter(area__gte=20)

    if intent.searchable_terms:
        vector = SearchVector("title", "description", "address", "ward__name", "ward__district__name", config="simple")
        search_query = SearchQuery(" ".join(intent.searchable_terms), config="simple")
        searched = narrowed.annotate(rank=SearchRank(vector, search_query)).filter(rank__gte=0.03).order_by("-rank", "-created_at")
        if searched.exists():
            return SearchResult(searched, intent)

    if narrowed.exists():
        intent.fallback_used = True
        return SearchResult(narrowed.order_by("-created_at"), intent)

    intent.fallback_used = True
    return SearchResult(queryset.order_by("-created_at"), intent)


def apply_roommate_keyword_search(queryset, query):
    intent = extract_keyword_intent(query)
    if not intent.has_signal:
        intent.fallback_used = bool(query)
        return SearchResult(queryset.order_by("-created_at"), intent)

    narrowed = queryset
    ceiling = extract_price_ceiling(query)
    if ceiling is not None:
        narrowed = narrowed.filter(models.Q(budget_min__lte=ceiling) | models.Q(budget_min__isnull=True))
    if "female" in intent.matched_intents:
        narrowed = narrowed.filter(gender_preference__in=["any", "female", "same"])
    if "male" in intent.matched_intents:
        narrowed = narrowed.filter(gender_preference__in=["any", "male", "same"])

    if intent.searchable_terms:
        vector = SearchVector("title", "description", "address", "university__name", "ward__name", config="simple")
        search_query = SearchQuery(" ".join(intent.searchable_terms), config="simple")
        searched = narrowed.annotate(rank=SearchRank(vector, search_query)).filter(rank__gte=0.03).order_by("-rank", "-created_at")
        if searched.exists():
            return SearchResult(searched, intent)

    if narrowed.exists():
        intent.fallback_used = True
        return SearchResult(narrowed.order_by("-created_at"), intent)

    intent.fallback_used = True
    return SearchResult(queryset.order_by("-created_at"), intent)

"""Deterministic Multilingual Script Detection and Trie-Based Transliteration Router."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.logging import get_logger
from src.modules.retrieval.domain.models import QueryScript

logger = get_logger(__name__)

DATA_FILE = Path(__file__).resolve().parent.parent / "infrastructure" / "transliteration_data.json"


@dataclass
class ScriptRoutingResult:
    """Outcome of script detection and concept transliteration to canonical English."""

    original_query: str
    detected_script: QueryScript
    translated_concept_query: str
    is_transliterated: bool
    mapped_terms: list[tuple[str, str]] = field(default_factory=list)
    unmapped_terms: list[str] = field(default_factory=list)


class TrieNode:
    """Node in prefix trie for token and multi-word phrase matching."""

    def __init__(self) -> None:
        self.children: dict[str, TrieNode] = {}
        self.translation: str | None = None
        self.is_terminal: bool = False


class TransliterationTrie:
    """Prefix trie for deterministic phrase matching and concept transliteration."""

    def __init__(self) -> None:
        self.root = TrieNode()

    def insert(self, phrase: str, translation: str) -> None:
        node = self.root
        tokens = phrase.lower().strip().split()
        for tok in tokens:
            if tok not in node.children:
                node.children[tok] = TrieNode()
            node = node.children[tok]
        node.is_terminal = True
        node.translation = translation

    def match_longest(self, tokens: list[str], start_idx: int) -> tuple[int, str | None]:
        """Match longest sequence of tokens starting at start_idx.

        Returns (num_tokens_matched, translation).
        """
        node = self.root
        best_match_len = 0
        best_translation: str | None = None
        curr_idx = start_idx

        while curr_idx < len(tokens) and tokens[curr_idx] in node.children:
            node = node.children[tokens[curr_idx]]
            curr_idx += 1
            if node.is_terminal and node.translation is not None:
                best_match_len = curr_idx - start_idx
                best_translation = node.translation

        return best_match_len, best_translation


class ScriptRouter:
    """Identifies query script by Unicode block and maps terms to canonical English."""

    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or DATA_FILE
        self.meetei_trie = TransliterationTrie()
        self.bengali_trie = TransliterationTrie()
        self.romanized_trie = TransliterationTrie()
        self.acronym_map: dict[str, str] = {}
        self._load_dictionary()

    def _load_dictionary(self) -> None:
        if not self.data_path.exists():
            logger.warning("Transliteration data file not found at %s", self.data_path)
            return

        with open(self.data_path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        for phrase, eng in data.get("meetei_mayek", {}).items():
            self.meetei_trie.insert(phrase, eng)

        for phrase, eng in data.get("bengali_script", {}).items():
            self.bengali_trie.insert(phrase, eng)

        for phrase, eng in data.get("romanized_meiteilon", {}).items():
            self.romanized_trie.insert(phrase, eng)

        self.acronym_map = data.get("acronyms", {})

    @staticmethod
    def detect_script(query: str) -> QueryScript:
        """Classify script by Unicode character distributions."""
        meetei_chars = 0
        bengali_chars = 0
        latin_chars = 0

        for ch in query:
            code = ord(ch)
            if (0xABC0 <= code <= 0xABFF) or (0xAAE0 <= code <= 0xAAFF):
                meetei_chars += 1
            elif 0x0980 <= code <= 0x09FF:
                bengali_chars += 1
            elif (0x0041 <= code <= 0x005A) or (0x0061 <= code <= 0x007A):
                latin_chars += 1

        if meetei_chars > 0 and meetei_chars >= bengali_chars:
            return QueryScript.MEETEI_MAYEK
        if bengali_chars > 0:
            return QueryScript.BENGALI
        return QueryScript.LATIN

    def route_query(self, query: str) -> ScriptRoutingResult:
        """Route query and transliterate concepts to canonical English for retrieval."""
        script = self.detect_script(query)
        clean_tokens = query.strip().split()
        if not clean_tokens:
            return ScriptRoutingResult(
                original_query=query,
                detected_script=script,
                translated_concept_query=query,
                is_transliterated=False,
            )

        # Select appropriate trie based on detected script
        if script == QueryScript.MEETEI_MAYEK:
            active_trie = self.meetei_trie
        elif script == QueryScript.BENGALI:
            active_trie = self.bengali_trie
        else:
            active_trie = self.romanized_trie

        translated_parts: list[str] = []
        mapped_terms: list[tuple[str, str]] = []
        unmapped_terms: list[str] = []
        i = 0

        while i < len(clean_tokens):
            match_len, translation = active_trie.match_longest([t.lower() for t in clean_tokens], i)
            if match_len > 0 and translation is not None:
                original_phrase = " ".join(clean_tokens[i : i + match_len])
                translated_parts.append(translation)
                mapped_terms.append((original_phrase, translation))
                i += match_len
            else:
                curr_tok = clean_tokens[i]
                translated_parts.append(curr_tok)
                if script in (QueryScript.MEETEI_MAYEK, QueryScript.BENGALI):
                    unmapped_terms.append(curr_tok)
                i += 1

        is_transliterated = len(mapped_terms) > 0
        translated_concept_query = " ".join(translated_parts)

        return ScriptRoutingResult(
            original_query=query,
            detected_script=script,
            translated_concept_query=translated_concept_query,
            is_transliterated=is_transliterated,
            mapped_terms=mapped_terms,
            unmapped_terms=unmapped_terms,
        )

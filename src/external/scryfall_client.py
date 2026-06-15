# src/external/scryfall_client.py
"""
Scryfall Client for MTG JudgeBot

Looks up card Oracle text and official rulings via the Scryfall API (free, no key needed).
Respects the 50ms rate limit between requests.
"""

from __future__ import annotations

import re
import time
from typing import List, Dict, Any, Optional

import requests

SCRYFALL_BASE = "https://api.scryfall.com"
REQUEST_DELAY = 0.075  # 75ms between requests (Scryfall asks for 50-100ms)
HEADERS = {"User-Agent": "MTGJudgeBot/1.0 (github.com/njaffe/mtg_judgebot)"}

# Common MTG terms that look like card names but aren't
NON_CARD_NAMES = {
    "magic", "the gathering", "magic the gathering", "mtg", "commander",
    "edh", "modern", "standard", "legacy", "vintage", "pioneer", "pauper",
    "brawl", "draft", "sealed", "limited", "constructed", "format",
    "creature", "instant", "sorcery", "enchantment", "artifact", "planeswalker",
    "land", "tribal", "battle", "kindred",
    "graveyard", "battlefield", "exile", "library", "hand", "stack",
    "combat", "upkeep", "draw", "main phase", "end step",
    "player", "opponent", "controller", "owner",
    "counter", "token", "emblem", "mana", "life", "damage",
    "tap", "untap", "cast", "activate", "trigger", "resolve",
    "target", "choose", "sacrifice", "destroy", "exile", "return",
    "etb", "enters the battlefield", "dies", "leaves the battlefield",
    "priority", "stack", "layer", "timestamp",
    "color identity", "color", "colorless", "multicolor",
    "shroud", "hexproof", "indestructible", "deathtouch", "lifelink",
    "flying", "trample", "haste", "vigilance", "reach", "menace",
    "first strike", "double strike", "flash", "defender",
    "equip", "equipment", "aura", "attach",
    "explore", "explores",
    # Common question words and format names that get capitalized
    "what", "when", "where", "which", "how", "does", "will", "would", "could",
    "dimir", "simic", "golgari", "orzhov", "izzet", "selesnya", "boros",
    "gruul", "azorius", "rakdos", "jund", "naya", "esper", "mardu", "temur",
    "abzan", "jeskai", "sultai", "can", "have", "this", "that", "there",
    "if", "my", "your", "their", "its", "also", "then", "but", "both",
    "each", "all", "any", "some", "after", "before", "during", "since",
    "while", "being", "are", "was", "not", "with", "about", "into",
    "does", "do", "did", "is", "has", "had", "may", "might", "shall",
    "should", "must", "still", "just", "only", "no", "yes",
    "mountain", "island", "forest", "swamp", "plains",  # basic land types
    "planeswalker", "planeswalkers",
}


class ScryfallClient:
    """Client for looking up card data from Scryfall."""

    def __init__(self):
        self._last_request_time = 0.0

    def _rate_limit(self):
        """Enforce rate limiting between Scryfall API calls."""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    def extract_card_names(self, query: str) -> List[str]:
        """
        Extract potential card names from a user query.

        Strategies:
        1. Quoted strings (single or double quotes)
        2. Capitalized multi-word sequences that look like card names
        3. Known card name patterns (possessives like "Galadriel's Dismissal")
        """
        names = []

        # Strategy 1: Quoted strings
        quoted = re.findall(r"""['"]([^'"]{2,50})['"]""", query)
        for q in quoted:
            if q.lower() not in NON_CARD_NAMES:
                names.append(q)

        # Strategy 2: Capitalized multi-word sequences (2-6 words)
        # Matches sequences like "Ghost of Ramirez DePietro", "Animate Dead",
        # "Leyline of the Void", "Thalia, Guardian of Thraben"
        # Connectors: of, the, in, to, from, for, with (NOT "and" — it usually separates card names)
        cap_pattern = r"\b([A-Z][a-zA-Z]+(?:'s)?(?:[,]?\s+(?:of|the|in|to|from|for|with))*(?:[,]?\s+[A-Z][a-zA-Z]+(?:'s)?)+)\b"
        capitalized = re.findall(cap_pattern, query)
        for match in capitalized:
            clean = match.strip().rstrip(",")
            # Strip leading non-card words (sentence starters like "If", "Does", "When")
            words = clean.split()
            while words and words[0].lower().rstrip(",") in NON_CARD_NAMES:
                words.pop(0)
            if not words:
                continue
            clean = " ".join(words)
            if clean.lower() not in NON_CARD_NAMES and len(clean) > 3:
                # Don't add if it's a substring of an already-found name
                if not any(clean in existing for existing in names):
                    names.append(clean)

        # Strategy 3: Single capitalized words that could be card names
        # Many MTG cards have single-word names (e.g., "Farewell", "Humility", "Opalescence")
        single_cap = re.findall(r"\b([A-Z][a-z]{3,}(?:'s)?)\b", query)
        already_found_lower = {n.lower() for n in names}
        # Also skip words that are part of already-found multi-word names
        already_found_words = set()
        for n in names:
            for w in n.lower().replace("'s", "").split():
                already_found_words.add(w)
        for word in single_cap:
            if (word.lower() not in NON_CARD_NAMES
                    and word.lower() not in already_found_lower
                    and word.lower() not in already_found_words
                    and len(word) > 4):
                names.append(word)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for name in names:
            lower = name.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(name)

        return unique

    def lookup_card(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Look up a single card by name using Scryfall's fuzzy search.

        Returns card data dict or None if not found.
        """
        self._rate_limit()

        try:
            resp = requests.get(
                f"{SCRYFALL_BASE}/cards/named",
                params={"fuzzy": name},
                headers=HEADERS,
                timeout=10,
            )

            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()

            card = {
                "name": data.get("name", ""),
                "mana_cost": data.get("mana_cost", ""),
                "type_line": data.get("type_line", ""),
                "oracle_text": data.get("oracle_text", ""),
                "colors": data.get("colors", []),
                "color_identity": data.get("color_identity", []),
                "legalities": data.get("legalities", {}),
                "scryfall_uri": data.get("scryfall_uri", ""),
                "rulings": [],
            }

            # Handle double-faced cards
            if not card["oracle_text"] and "card_faces" in data:
                faces = data["card_faces"]
                oracle_parts = []
                for face in faces:
                    face_name = face.get("name", "")
                    face_text = face.get("oracle_text", "")
                    if face_text:
                        oracle_parts.append(f"[{face_name}] {face_text}")
                card["oracle_text"] = "\n\n".join(oracle_parts)
                if not card["mana_cost"] and faces:
                    card["mana_cost"] = faces[0].get("mana_cost", "")

            # Fetch rulings
            rulings_uri = data.get("rulings_uri")
            if rulings_uri:
                self._rate_limit()
                try:
                    rulings_resp = requests.get(rulings_uri, headers=HEADERS, timeout=10)
                    if rulings_resp.status_code == 200:
                        rulings_data = rulings_resp.json().get("data", [])
                        card["rulings"] = [
                            {"date": r.get("published_at", ""), "comment": r.get("comment", "")}
                            for r in rulings_data
                        ]
                except Exception:
                    pass  # Rulings are supplementary; don't fail the whole lookup

            return card

        except requests.RequestException:
            return None

    def lookup_cards(self, query: str) -> List[Dict[str, Any]]:
        """
        Extract card names from a query and look them all up.

        Returns list of card data dicts (only cards that were found).
        """
        names = self.extract_card_names(query)
        cards = []
        for name in names:
            card = self.lookup_card(name)
            if card:
                cards.append(card)
        return cards

    @staticmethod
    def format_card_data(cards: List[Dict[str, Any]]) -> str:
        """
        Format card data into a string suitable for inclusion in an LLM prompt.
        """
        if not cards:
            return ""

        parts = []
        for card in cards:
            lines = [
                f"Card: {card['name']}",
                f"Mana Cost: {card['mana_cost']}" if card.get("mana_cost") else None,
                f"Type: {card['type_line']}",
                f"Oracle Text: {card['oracle_text']}",
                f"Color Identity: {', '.join(card['color_identity']) if card['color_identity'] else 'Colorless'}",
            ]
            # Include up to 5 most relevant rulings
            if card.get("rulings"):
                lines.append("Official Rulings:")
                for ruling in card["rulings"][:5]:
                    lines.append(f"  - ({ruling['date']}) {ruling['comment']}")

            parts.append("\n".join(line for line in lines if line is not None))

        return "\n\n---\n\n".join(parts)


if __name__ == "__main__":
    client = ScryfallClient()

    # Test extraction
    test_query = "Can I return a card with Ghost of Ramirez DePietro's ability after Francisco explores?"
    names = client.extract_card_names(test_query)
    print(f"Extracted names: {names}")

    # Test lookup
    for name in names:
        card = client.lookup_card(name)
        if card:
            print(f"\n{card['name']}: {card['oracle_text'][:100]}...")

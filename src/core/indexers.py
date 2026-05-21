"""
Database Indexers for MTG Judge Bot

This module provides service classes for database indexing operations using FAISS.
Includes a rule-aware parser for the Magic: The Gathering Comprehensive Rules.
"""

from __future__ import annotations

import os
import re
import shutil
import pickle
import faiss
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Max chunk size before splitting a rule group into sub-chunks
MAX_CHUNK_CHARS = 3000

# Default local embedding model (runs on CPU, no API key needed)
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class DatabaseIndexer:
    """
    Service class for database indexing operations using FAISS.
    Uses sentence-transformers for local embeddings (no API key needed).
    """

    def __init__(
        self,
        faiss_index_path: Optional[str] = None,
        data_path: Optional[str] = None,
        raw_docs_path: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        self.faiss_index_path = faiss_index_path or os.getenv("FAISS_INDEX_PATH")
        self.data_path = data_path or os.getenv("DATA_PATH")
        self.raw_docs_path = raw_docs_path or os.getenv("RAW_DOCS_PATH")
        self.embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)

        if not all([self.faiss_index_path, self.data_path, self.raw_docs_path]):
            raise ValueError("FAISS_INDEX_PATH, DATA_PATH, and RAW_DOCS_PATH are required")

        self._encoder = None  # Lazy-loaded

    def _get_encoder(self):
        """Lazy-load the sentence-transformers model."""
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {self.embedding_model}")
            self._encoder = SentenceTransformer(self.embedding_model)
        return self._encoder

    def _load_single_large_text_file(self, file_path: str) -> str:
        """Load a single large text file and return its content."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"Loaded file: {file_path} with {len(content)} characters.")
        return content

    # ------------------------------------------------------------------ #
    #  Rule-aware parser for the MTG Comprehensive Rules                  #
    # ------------------------------------------------------------------ #

    def _split_rules_and_glossary(self, text: str) -> Tuple[str, str]:
        """Split the CR text into the rules section and the glossary section."""
        # The glossary starts with a standalone "Glossary" line after the rules
        # (there's also one in the table of contents, so find the LAST one before Credits)
        glossary_match = None
        for m in re.finditer(r"^Glossary\s*$", text, re.MULTILINE):
            glossary_match = m
        if glossary_match:
            rules_text = text[:glossary_match.start()]
            # Find where Credits start to exclude them from glossary
            credits_match = re.search(r"^Credits\s*$", text[glossary_match.end():], re.MULTILINE)
            if credits_match:
                glossary_text = text[glossary_match.end():glossary_match.end() + credits_match.start()]
            else:
                glossary_text = text[glossary_match.end():]
            return rules_text, glossary_text
        return text, ""

    def _parse_rules_section(self, rules_text: str) -> List[Dict[str, Any]]:
        """
        Parse the numbered rules into structured chunks.

        Groups each top-level rule (e.g., 702.16.) with all its lettered subrules
        (702.16a, 702.16b, ...) and any Example: lines as a single chunk.
        """
        # Pattern matches rule numbers like: 100. / 100.1. / 100.1a / 702.16b
        # Subrules (e.g. 608.2a) do NOT have a trailing dot — they end with letter+space
        # So we match: digits.digits(letter)? followed by either a dot or whitespace
        rule_pattern = re.compile(r"^(\d{3})\.(\d+)?([a-z])?(?:\.|\s)", re.MULTILINE)

        chunks = []
        lines = rules_text.split("\n")

        current_rule_num = None  # e.g., "702.16"
        current_lines: List[str] = []
        current_subrules: List[str] = []

        def _flush_current():
            """Save the current rule group as a chunk."""
            if not current_lines or current_rule_num is None:
                return
            content = "\n".join(current_lines).strip()
            if not content:
                return
            subrule_str = ", ".join(current_subrules) if current_subrules else ""
            chunks.append({
                "content": content,
                "metadata": {
                    "type": "rule",
                    "rule": current_rule_num,
                    "subrules": subrule_str,
                },
            })

        for line in lines:
            match = rule_pattern.match(line)
            if match:
                section = match.group(1)  # e.g., "702"
                number = match.group(2)   # e.g., "16" or None
                letter = match.group(3)   # e.g., "a" or None

                if number is None:
                    # Section-level rule like "702." — start a new group
                    _flush_current()
                    current_rule_num = f"{section}"
                    current_lines = [line]
                    current_subrules = []
                elif letter is None:
                    # Top-level numbered rule like "702.16." — start a new group
                    _flush_current()
                    current_rule_num = f"{section}.{number}"
                    current_lines = [line]
                    current_subrules = []
                else:
                    # Subrule like "702.16a" — append to current group
                    rule_id = f"{section}.{number}{letter}"
                    if current_rule_num and current_rule_num == f"{section}.{number}":
                        # Same parent — add to current group
                        current_lines.append(line)
                        current_subrules.append(rule_id)
                    else:
                        # Different parent or first subrule without parent header
                        _flush_current()
                        current_rule_num = f"{section}.{number}"
                        current_lines = [line]
                        current_subrules = [rule_id]
            else:
                # Non-rule line: could be Example:, blank line, or continuation
                if current_lines is not None:
                    current_lines.append(line)

        # Flush the last group
        _flush_current()

        return chunks

    def _parse_glossary_section(self, glossary_text: str) -> List[Dict[str, Any]]:
        """
        Parse the glossary into individual term chunks.

        Glossary entries are separated by blank lines.
        The first line of each entry is the term name.
        """
        chunks = []
        entries = re.split(r"\n\n+", glossary_text.strip())

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            # First line is the term name
            lines = entry.split("\n", 1)
            term = lines[0].strip()
            if not term:
                continue
            chunks.append({
                "content": entry,
                "metadata": {
                    "type": "glossary",
                    "term": term,
                },
            })

        return chunks

    def _split_large_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Split chunks that exceed MAX_CHUNK_CHARS at natural subrule boundaries.

        For large rule groups, splits at subrule boundaries while prepending
        the parent rule text to each sub-chunk for context.
        """
        result = []
        for chunk in chunks:
            if len(chunk["content"]) <= MAX_CHUNK_CHARS:
                result.append(chunk)
                continue

            # Split at subrule boundaries
            content = chunk["content"]
            metadata = chunk["metadata"]
            rule_num = metadata.get("rule", "")

            # Find the parent rule line(s) — everything before the first subrule
            # Subrules like 608.2a have no trailing dot — match letter+space
            subrule_pattern = re.compile(
                r"^(\d{3}\.\d+[a-z])[\s.]", re.MULTILINE
            )
            first_subrule = subrule_pattern.search(content)

            if not first_subrule:
                # No subrules to split on — keep as-is
                result.append(chunk)
                continue

            parent_text = content[:first_subrule.start()].strip()

            # Split into subrule segments
            matches = list(subrule_pattern.finditer(content))
            segments = []
            for i, m in enumerate(matches):
                start = m.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
                segments.append((m.group(1), content[start:end].strip()))

            # Group segments into sub-chunks under MAX_CHUNK_CHARS
            current_content = parent_text
            current_subrules = []

            for subrule_id, segment_text in segments:
                candidate = current_content + "\n\n" + segment_text if current_content else segment_text
                if len(candidate) > MAX_CHUNK_CHARS and current_content != parent_text:
                    # Flush current sub-chunk
                    result.append({
                        "content": current_content,
                        "metadata": {
                            "type": "rule",
                            "rule": rule_num,
                            "subrules": ", ".join(current_subrules),
                        },
                    })
                    # Start new sub-chunk with parent context
                    current_content = parent_text + "\n\n" + segment_text
                    current_subrules = [subrule_id]
                else:
                    current_content = candidate
                    current_subrules.append(subrule_id)

            # Flush remaining
            if current_content.strip():
                result.append({
                    "content": current_content,
                    "metadata": {
                        "type": "rule",
                        "rule": rule_num,
                        "subrules": ", ".join(current_subrules),
                    },
                })

        return result

    def _parse_comprehensive_rules(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse the full Comprehensive Rules into structured, rule-aware chunks.
        """
        rules_text, glossary_text = self._split_rules_and_glossary(text)

        rule_chunks = self._parse_rules_section(rules_text)
        glossary_chunks = self._parse_glossary_section(glossary_text)

        # Split oversized chunks
        rule_chunks = self._split_large_chunks(rule_chunks)

        all_chunks = rule_chunks + glossary_chunks

        # Stats
        rule_count = sum(1 for c in all_chunks if c["metadata"].get("type") == "rule")
        glossary_count = sum(1 for c in all_chunks if c["metadata"].get("type") == "glossary")
        avg_len = sum(len(c["content"]) for c in all_chunks) / max(len(all_chunks), 1)
        print(f"Parsed {rule_count} rule chunks + {glossary_count} glossary entries = {len(all_chunks)} total chunks")
        print(f"Average chunk size: {avg_len:.0f} chars")

        return all_chunks

    # ------------------------------------------------------------------ #
    #  Embedding & FAISS storage                                          #
    # ------------------------------------------------------------------ #

    def _embed_texts(self, texts: List[str]):
        """Embed a list of texts using sentence-transformers (local, no API key)."""
        encoder = self._get_encoder()
        print(f"  Embedding {len(texts)} texts locally...")
        embeddings = encoder.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        return [np.array(emb, dtype=np.float32) for emb in embeddings]

    def _save_to_faiss(self, documents):
        """Save documents and embeddings to a FAISS index."""
        if os.path.exists(self.faiss_index_path):
            shutil.rmtree(self.faiss_index_path)
        os.makedirs(self.faiss_index_path, exist_ok=True)

        texts = [doc["content"] for doc in documents]
        embeddings = self._embed_texts(texts)

        dim = int(len(embeddings[0]))
        index = faiss.IndexFlatL2(dim)
        index.add(np.vstack(embeddings))

        # Save FAISS index
        faiss.write_index(index, os.path.join(self.faiss_index_path, "faiss.index"))

        # Save documents (with metadata)
        with open(os.path.join(self.faiss_index_path, "documents.pkl"), "wb") as f:
            pickle.dump(documents, f)

        print(f"Saved {len(documents)} chunks and embeddings to {self.faiss_index_path}.")

    def create_database_from_large_file(self):
        """Create database from the first .txt file in data/raw_docs_path."""
        raw_dir = os.path.join(self.data_path, self.raw_docs_path)
        files = [f for f in os.listdir(raw_dir) if f.endswith(".txt")]
        if not files:
            raise FileNotFoundError(f"No .txt files found in {raw_dir}")

        large_text_file_path = os.path.join(raw_dir, files[0])
        print(f"Creating FAISS database from {large_text_file_path} into {self.faiss_index_path}...")

        content = self._load_single_large_text_file(large_text_file_path)
        chunks = self._parse_comprehensive_rules(content)
        self._save_to_faiss(chunks)

        print("Database creation completed successfully!")

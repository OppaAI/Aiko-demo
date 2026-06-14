"""
core/memorize.py
Aiko's persistent memory — custom backend via sqlite-vec + fastembed + Modal LLM.
Abstracts all memory calls so think.py stays clean.

Memory lifecycle:
  - Every search() call increments access_count and updates last_accessed_at
    in the memories table, enabling Ebbinghaus-style exponential decay scoring.
  - cleanup() deletes memories below decay threshold, with grace period
    protection for newly created entries.
  - Decay logic lives in core/forget.py (pure math, no I/O).
  - Pinned memories (created via pin()) are permanently immune to decay
    cleanup. The pinned flag lives in the memories table.

Storage layout (single .db file):
  memories        — canonical record: id, user_id, memory, metadata
  memories_fts    — FTS5 virtual table for lexical search (BM25)
  memories_vec    — vec0 virtual table for KNN cosine search

Recall strategy — Reciprocal Rank Fusion (RRF):
  score = 1/(k + rank_knn) + 1/(k + rank_fts)
  k=60 (standard RRF constant — dampens outlier ranks)

  KNN catches semantic similarity ("I love cats" ↔ "I adore cats")
  FTS5 catches exact token matches ("Max", "birthday", proper nouns)
  RRF fuses both without weighting either arbitrarily.

Custom backend (replaces Qdrant + mem0):
  - _MemoryBackend handles LLM-based fact extraction, fastembed embeddings,
    and direct sqlite-vec upsert/search/delete/scroll.
  - Extraction prompt is tuned for small models: asks for a JSON array of
    atomic facts, strips <think> blocks for CoT models, skips trivial turns.
  - All schema fields (memory, user_id, created_at, access_count,
    last_accessed_at, pinned) are owned by this module — no hidden schema.

Extraction LLM:
  - Uses LLAMA_BASE_URL (Modal OpenAI-compat endpoint) + LLAMA_API_KEY.

Dependencies:
  pip install sqlite-vec fastembed
"""
from dotenv import load_dotenv
load_dotenv()

import json
import os
import re
import sqlite3
import struct
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import sqlite_vec
from fastembed import TextEmbedding

from core.forget import compute_weighted_score, should_cleanup, CLEANUP_THRESHOLD
from core.log import get_logger

log = get_logger(__name__)

# ── boot labels ───────────────────────────────────────────────────────────────

BOOT_LABELS = {
    'mem_sqlite_vec': 'Opening sqlite-vec memory store...',
    'mem_embed':      'Loading fastembed model...',
    'mem_cleanup':    'Running memory cleanup...',
    'mem_ready':      'Memory backend ready',
}

# ── constants ─────────────────────────────────────────────────────────────────

EMBED_MODEL = "BAAI/bge-base-en-v1.5"
EMBED_DIMS  = 768
RRF_K       = 60    # standard RRF constant — dampens outlier ranks
KNN_LIMIT   = 20    # candidates fetched before RRF re-rank
FTS_LIMIT   = 20    # candidates fetched before RRF re-rank

USER_ID = os.getenv("USER_ID", "Guest")

# Minimum conversation size (chars) worth sending to LLM for extraction.
# Skips trivial turns (greetings, one-word replies) to save inference time.
_EXTRACT_MIN_CHARS = int(os.getenv("MEMORY_EXTRACT_MIN_CHARS", 80))

# Extraction prompt — tuned for small models.
# {user_id} and {conversation} are formatted at call time so facts are always
# scoped to the correct user, not hardcoded to a specific name.
_EXTRACT_PROMPT = """\
Extract memorable facts about the USER from this conversation.
The USER is {user_id}. The ASSISTANT is Aiko.
Write every fact from Aiko's perspective, using second-person for the user.
Example format: "Oppa's birthday is June 3, 2026"  "Oppa created you (Aiko) recently"
Return ONLY a JSON array of short strings. Each string is one atomic fact.
Facts should be about the user's preferences, identity, life, or goals.
If nothing is worth remembering, return: []
Do NOT include facts about Aiko's own behavior or feelings.
Do NOT explain. No markdown.

Conversation:
{conversation}"""


def _sanitize_fts_query(query: str) -> str:
    """
    Strip characters that break FTS5 query parsing.
    FTS5 treats , " ( ) * ^ : - ' as syntax tokens — remove them all.
    """
    cleaned = re.sub(r'[^\w\s]', ' ', query)
    cleaned = ' '.join(cleaned.split())
    return cleaned or "*"


# ── schema ────────────────────────────────────────────────────────────────────

_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS memories (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL,
    memory           TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    access_count     INTEGER NOT NULL DEFAULT 0,
    last_accessed_at TEXT NOT NULL DEFAULT 'never',
    pinned           INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    memory,
    id UNINDEXED,
    content='memories',
    content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_vec USING vec0(
    id TEXT PRIMARY KEY,
    embedding FLOAT[{dims}]
);

CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, memory, id)
    VALUES (new.rowid, new.memory, new.id);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, memory, id)
    VALUES ('delete', old.rowid, old.memory, old.id);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE OF memory ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, memory, id)
    VALUES ('delete', old.rowid, old.memory, old.id);
    INSERT INTO memories_fts(rowid, memory, id)
    VALUES (new.rowid, new.memory, new.id);
END;
""".format(dims=EMBED_DIMS)


# ── sqlite helpers ────────────────────────────────────────────────────────────

def _sqlite_get_payload(conn: sqlite3.Connection, mem_id: str) -> dict:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM memories WHERE id = ?", (mem_id,)
    ).fetchone()
    return dict(row) if row else {}


def _sqlite_set_payload(conn: sqlite3.Connection, mem_id: str, payload: dict) -> None:
    if not payload:
        return
    cols = ", ".join(f"{k} = ?" for k in payload)
    vals = list(payload.values()) + [mem_id]
    conn.execute(f"UPDATE memories SET {cols} WHERE id = ?", vals)
    conn.commit()


def _sqlite_batch_get_payloads(conn: sqlite3.Connection, mem_ids: list[str]) -> dict:
    if not mem_ids:
        return {}
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(mem_ids))
    rows = conn.execute(
        f"SELECT id, access_count, last_accessed_at FROM memories WHERE id IN ({placeholders})",
        mem_ids,
    ).fetchall()
    return {
        r["id"]: (r["access_count"] or 0, r["last_accessed_at"] or "never")
        for r in rows
    }


def _sqlite_is_pinned(conn: sqlite3.Connection, mem_id: str) -> bool:
    row = conn.execute(
        "SELECT pinned FROM memories WHERE id = ?", (mem_id,)
    ).fetchone()
    return bool(row and row[0])


def _sqlite_knn_search(
    conn: sqlite3.Connection,
    vector: list[float],
    user_id: str,
    limit: int,
) -> list[sqlite3.Row]:
    vec_blob = sqlite_vec.serialize_float32(vector)
    rows = conn.execute(
        """
        SELECT v.id, vec_distance_cosine(v.embedding, ?) AS dist
        FROM memories_vec v
        JOIN memories m ON m.id = v.id
        WHERE m.user_id = ?
        ORDER BY dist ASC
        LIMIT ?
        """,
        (vec_blob, user_id, limit),
    ).fetchall()
    return rows


# ── extraction LLM call ───────────────────────────────────────────────────────

def _call_extraction_llm(prompt: str, base_url: str, api_key: str) -> str:
    """
    Send the extraction prompt to the Modal OpenAI-compat endpoint.
    Raises on failure — caller catches and returns [].
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    resp = httpx.post(
        base_url.rstrip('/'),
        headers=headers,
        json={
            "messages":    [{"role": "user", "content": prompt}],
            "stream":      False,
            "temperature": 0.1,
            "max_tokens":  512,
        },
        timeout=45,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── memory backend ────────────────────────────────────────────────────────────

class _MemoryBackend:
    """
    sqlite-vec + FTS5 + RRF backend.
    Public API: add(), search(), get_all(), delete(), delete_all()
    """

    def __init__(
        self,
        db_path:         str,
        llama_base_url:  str,
        llama_api_key:   str,
        fastembed_cache: Optional[str] = None,
    ) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path        = db_path
        self._llama_base_url = llama_base_url
        self._llama_api_key  = llama_api_key
        self._embedder = TextEmbedding(
            model_name=EMBED_MODEL,
            cache_dir=fastembed_cache,
        )
        self._conn = self._connect()
        self._apply_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        sqlite_vec.load(conn)
        return conn

    def _apply_schema(self) -> None:
        self._conn.executescript(_DDL)
        self._conn.commit()

    def _embed(self, text: str) -> list[float]:
        return list(self._embedder.embed([text]))[0].tolist()

    # ── extraction ────────────────────────────────────────────────────────────

    def _should_extract(self, messages: list[dict]) -> bool:
        total = sum(
            len(m.get("content") or "")
            for m in messages
            if m.get("role") in ("user", "assistant")
            and (m.get("content") or "").strip()
        )
        return total >= _EXTRACT_MIN_CHARS

    def _extract_facts(self, messages: list[dict], user_id: str) -> list[str]:
        if not self._should_extract(messages):
            return []

        clean_messages = [
            m for m in messages
            if m.get("role") in ("user", "assistant")
            and (m.get("content") or "").strip()
        ]

        while clean_messages and clean_messages[0].get("role") != "user":
            clean_messages.pop(0)
        while len(clean_messages) > 1 and clean_messages[-1].get("role") == "assistant":
            if any(m.get("role") == "user" for m in clean_messages[:-1]):
                break
            clean_messages.pop()

        if not clean_messages:
            return []

        total = sum(len(m.get("content") or "") for m in clean_messages)
        if total < _EXTRACT_MIN_CHARS:
            return []

        convo = "\n".join(
            f"{m['role'].upper()}: {m['content'].strip()}"
            for m in clean_messages
        )
        prompt = _EXTRACT_PROMPT.format(user_id=user_id, conversation=convo)

        try:
            raw = _call_extraction_llm(
                prompt=prompt,
                base_url=self._llama_base_url,
                api_key=self._llama_api_key,
            )
        except Exception as e:
            log.warning("Extraction LLM call failed: %s", e)
            return []

        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()

        try:
            facts = json.loads(raw)
            if isinstance(facts, list):
                return [f.strip() for f in facts if isinstance(f, str) and f.strip()]
        except json.JSONDecodeError:
            log.warning("Failed to parse extraction JSON: %r", raw[:200])

        return []

    # ── write ─────────────────────────────────────────────────────────────────

    def add(self, messages: list[dict], user_id: str) -> list[str]:
        facts = self._extract_facts(messages, user_id=user_id)
        if not facts:
            return []

        now = datetime.now(timezone.utc).isoformat()
        ids = []

        for fact in facts:
            mem_id = str(uuid.uuid4())
            try:
                vector = self._embed(fact)
                self._conn.execute(
                    """
                    INSERT INTO memories
                        (id, user_id, memory, created_at, access_count, last_accessed_at, pinned)
                    VALUES (?, ?, ?, ?, 0, 'never', 0)
                    """,
                    (mem_id, user_id, fact, now),
                )
                self._conn.execute(
                    "INSERT INTO memories_vec(id, embedding) VALUES (?, ?)",
                    (mem_id, sqlite_vec.serialize_float32(vector)),
                )
                self._conn.commit()
                ids.append(mem_id)
            except Exception as e:
                log.warning("Failed to upsert fact %r: %s", mem_id, e)
                self._conn.rollback()

        return ids

    # ── read ──────────────────────────────────────────────────────────────────

    def search(self, query: str, user_id: str, limit: int = 5) -> list[dict]:
        vector   = self._embed(query)
        knn_rows = _sqlite_knn_search(self._conn, vector, user_id, KNN_LIMIT)
        rank_knn = {row["id"]: i + 1 for i, row in enumerate(knn_rows)}

        fts_rows = self._conn.execute(
            """
            SELECT f.id
            FROM memories_fts f
            JOIN memories m ON m.id = f.id
            WHERE memories_fts MATCH ?
            AND m.user_id = ?
            ORDER BY rank
            LIMIT ?
            """,
            (_sanitize_fts_query(query), user_id, FTS_LIMIT),
        ).fetchall()
        rank_fts = {row["id"]: i + 1 for i, row in enumerate(fts_rows)}

        all_ids = set(rank_knn) | set(rank_fts)
        if not all_ids:
            return []

        def rrf(mem_id: str) -> float:
            score = 0.0
            if mem_id in rank_knn:
                score += 1.0 / (RRF_K + rank_knn[mem_id])
            if mem_id in rank_fts:
                score += 1.0 / (RRF_K + rank_fts[mem_id])
            return score

        ranked       = sorted(all_ids, key=rrf, reverse=True)[:limit]
        placeholders = ",".join("?" * len(ranked))
        rows         = self._conn.execute(
            f"SELECT * FROM memories WHERE id IN ({placeholders})", ranked
        ).fetchall()

        order       = {mid: i for i, mid in enumerate(ranked)}
        rows_sorted = sorted(rows, key=lambda r: order.get(r["id"], 999))
        return [dict(r) for r in rows_sorted]

    def get_all(self, user_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE user_id = ?", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, memory_id: str) -> None:
        self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._conn.execute("DELETE FROM memories_vec WHERE id = ?", (memory_id,))
        self._conn.commit()

    def delete_all(self, user_id: str) -> None:
        ids = [
            r["id"] for r in self._conn.execute(
                "SELECT id FROM memories WHERE user_id = ?", (user_id,)
            ).fetchall()
        ]
        if not ids:
            return
        placeholders = ",".join("?" * len(ids))
        self._conn.execute(f"DELETE FROM memories WHERE id IN ({placeholders})", ids)
        self._conn.execute(f"DELETE FROM memories_vec WHERE id IN ({placeholders})", ids)
        self._conn.commit()


# ── memorize ──────────────────────────────────────────────────────────────────

class AikoMemorize:
    """
    Persistent memory with Ebbinghaus decay lifecycle.

    Uses _MemoryBackend (LLM extraction + fastembed + sqlite-vec).

    Env vars:
      LLAMA_BASE_URL       — Modal OpenAI-compat endpoint
      LLAMA_API_KEY        — Modal API key (optional)
      SQLITE_MEMORY_PATH   — path to .db file (default: ~/.aiko/memory.db)
                             Point this at a persistent volume on HF Space.
      FASTEMBED_CACHE_PATH — optional cache dir for fastembed model weights

    Boot sequence (called by wakeup.py):
        memorize = AikoMemorize()
        memorize.cleanup()

    Pinned memories are immune to cleanup() regardless of decay score.
    """

    def __init__(self, silent: bool = False) -> None:
        db_path = os.getenv(
            "SQLITE_MEMORY_PATH",
            str(Path.home() / ".aiko" / "memory.db"),
        )

        if not silent:
            log.info("Opening sqlite-vec memory store...")

        self._mem = _MemoryBackend(
            db_path=db_path,
            llama_base_url=os.getenv("LLAMA_BASE_URL", ""),
            llama_api_key=os.getenv("LLAMA_API_KEY", ""),
            fastembed_cache=os.getenv("FASTEMBED_CACHE_PATH"),
        )
        self._conn = self._mem._conn

        if not silent:
            log.info("Ready.")

    # ── write ─────────────────────────────────────────────────────────────────

    def add(self, messages: list[dict], user_id: str = USER_ID) -> bool:
        """
        Extract facts from a conversation turn and persist to memory.
        Returns True on success, False on failure.
        """
        try:
            t       = time.perf_counter()
            ids     = self._mem.add(messages, user_id=user_id)
            elapsed = time.perf_counter() - t
            if ids:
                log.info("Saved %d memories in %.2fs", len(ids), elapsed)
            else:
                log.debug("No facts extracted (%.2fs) — nothing saved.", elapsed)
            return True
        except Exception as e:
            log.error("Save failed: %s", e)
            return False

    def pin(self, messages: list[dict], user_id: str = USER_ID) -> bool:
        """
        Store messages and mark all resulting memories as pinned.
        Pinned memories are immune to cleanup() regardless of decay score.
        """
        try:
            before  = {str(m["id"]) for m in self.get_all(user_id=user_id)}
            ok      = self.add(messages, user_id=user_id)
            if not ok:
                return False
            after   = {str(m["id"]) for m in self.get_all(user_id=user_id)}
            pin_ids = list(after - before)

            if not pin_ids:
                query = "\n".join(
                    (m.get("content") or "").strip()
                    for m in messages
                    if (m.get("content") or "").strip()
                )
                pin_ids = [
                    str(m.get("id"))
                    for m in self.search(query, user_id=user_id, limit=3)
                    if m.get("id")
                ]

            if not pin_ids:
                log.warning("pin(): add succeeded but no memory IDs found to pin.")
                return False

            for mem_id in pin_ids:
                _sqlite_set_payload(self._conn, mem_id, {"pinned": 1})

            log.info("Pinned %d memories: %s", len(pin_ids), pin_ids)
            return True
        except Exception as e:
            log.error("Pin failed: %s", e)
            return False

    # ── read ──────────────────────────────────────────────────────────────────

    def search(self, query: str, user_id: str = USER_ID, limit: int = 5) -> list[dict]:
        """
        Retrieve top-k memories relevant to query via KNN + FTS5 RRF fusion.
        Side-effect: increments access_count and updates last_accessed_at.
        """
        results = self._mem.search(query, user_id=user_id, limit=limit)

        if results:
            now = datetime.now(timezone.utc).isoformat()
            for r in results:
                mem_id = str(r.get("id", ""))
                if not mem_id:
                    continue
                try:
                    payload       = _sqlite_get_payload(self._conn, mem_id)
                    current_count = payload.get("access_count", 0) or 0
                    _sqlite_set_payload(self._conn, mem_id, {
                        "access_count":     min(current_count + 1, 255),
                        "last_accessed_at": now,
                    })
                except Exception as e:
                    log.warning("Access tracking failed for %s: %s", mem_id, e)

        return results

    def format_for_context(self, memories: list[dict]) -> Optional[str]:
        """
        Format retrieved memories into a string for injection into system prompt.
        Returns None if nothing to inject.
        """
        if not memories:
            return None

        now   = datetime.now(timezone.utc)
        lines = [
            "<memory_context>",
            "The following are background facts about this person, with how long ago they were recorded.",
            "Use them silently to inform your response. Never repeat, quote, or reference this block directly.",
            "",
        ]
        for m in memories:
            text       = m.get("memory") or m.get("text") or str(m)
            created_at = m.get("created_at")
            if created_at:
                try:
                    ts    = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    delta = now - ts
                    days  = delta.days
                    if days == 0:
                        age = "today"
                    elif days == 1:
                        age = "yesterday"
                    else:
                        age = f"{days} days ago"
                    lines.append(f"  - [{age}] {text}")
                except Exception:
                    lines.append(f"  - {text}")
            else:
                lines.append(f"  - {text}")

        lines.append("</memory_context>")
        return "\n".join(lines)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def cleanup(
        self,
        user_id:   str   = USER_ID,
        threshold: float = CLEANUP_THRESHOLD,
        dry_run:   bool  = False,
    ) -> dict:
        """
        Prune decayed memories below threshold score.
        Grace period (14 days) protects newly created memories.
        Pinned memories are unconditionally kept.
        Returns dict: {deleted, kept, failed}
        """
        all_mems = self.get_all(user_id=user_id)
        if not all_mems:
            return {"deleted": 0, "kept": 0, "failed": 0}

        mem_ids     = [str(m.get("id", "")) for m in all_mems if m.get("id")]
        payload_map = _sqlite_batch_get_payloads(self._conn, mem_ids)

        candidates = []
        kept       = 0

        for m in all_mems:
            mem_id     = str(m.get("id", ""))
            ac, la     = payload_map.get(mem_id, (0, "never"))
            created_at = m.get("created_at", "")

            if _sqlite_is_pinned(self._conn, mem_id):
                kept += 1
                continue

            if should_cleanup(ac, la, created_at):
                candidates.append({
                    "id":             mem_id,
                    "weighted_score": round(compute_weighted_score(ac, la), 4),
                })
            else:
                kept += 1

        candidates.sort(key=lambda x: x["weighted_score"])

        if dry_run:
            log.info("Dry run: %d candidates for deletion, %d kept.", len(candidates), kept)
            return {"deleted": 0, "kept": kept, "failed": 0, "candidates": candidates}

        deleted = 0
        failed  = 0
        for c in candidates:
            try:
                self._mem.delete(memory_id=c["id"])
                deleted += 1
            except Exception as e:
                log.warning("Cleanup delete failed for %s: %s", c["id"], e)
                failed += 1

        log.info("Cleanup: deleted=%d, kept=%d, failed=%d", deleted, kept, failed)
        return {"deleted": deleted, "kept": kept, "failed": failed}

    # ── debug ─────────────────────────────────────────────────────────────────

    def get_all(self, user_id: str = USER_ID) -> list[dict]:
        """Return all stored memories for a user."""
        return self._mem.get_all(user_id=user_id)

    def clear(self, user_id: str = USER_ID) -> None:
        """Wipe all memories for a user. Use carefully."""
        self._mem.delete_all(user_id=user_id)
        log.info("Cleared all memories for user '%s'.", user_id)
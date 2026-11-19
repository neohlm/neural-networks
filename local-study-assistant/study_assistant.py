from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # PDF ingestion is optional until the package is installed.
    PdfReader = None

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("STUDY_ASSISTANT_DB", ROOT / "data" / "study.db"))
DOCS_DIR = Path(os.environ.get("STUDY_ASSISTANT_DOCS", ROOT / "documents"))
BASE_URL = os.environ.get("UNSLOTH_BASE_URL", "http://localhost:8888/v1").rstrip("/")
MODEL = os.environ.get("UNSLOTH_MODEL")
KEYRING_SERVICE = "local-study-assistant"
KEYRING_USERNAME = "unsloth-api-key"


def supported_keyring():
    try:
        import keyring

        backend = keyring.get_keyring()
        module = type(backend).__module__
        supported = module.startswith(
            ("keyring.backends.SecretService", "keyring.backends.kwallet")
        )
        if not supported or getattr(backend, "priority", 0) <= 0:
            return None
        return keyring
    except Exception:
        return None


def load_api_key() -> str:
    environment_key = os.environ.get("UNSLOTH_API_KEY", "")
    if environment_key:
        return environment_key

    keyring = supported_keyring()
    if keyring is None:
        return ""
    try:
        return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME) or ""
    except Exception:
        return ""


def save_api_key() -> None:
    from getpass import getpass

    keyring = supported_keyring()
    if keyring is None:
        raise RuntimeError(
            "No supported Linux desktop keyring is available. Enable Secret Service "
            "(GNOME Keyring) or KWallet, then try again."
        )
    secret = getpass("Unsloth API key (input hidden): ").strip()
    if not secret:
        raise RuntimeError("No key entered; nothing was saved.")
    keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, secret)
    if keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME) != secret:
        raise RuntimeError("The desktop keyring did not confirm the saved key.")
    print("Unsloth API key saved in the desktop keyring.")


API_KEY = load_api_key()
CHUNK_CHARS = 1000
CHUNK_OVERLAP = 150


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5("
        "source UNINDEXED, page UNINDEXED, content, tokenize='porter unicode61')"
    )
    return conn


def extract_text(path: Path) -> list[tuple[str, str]]:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return [("", path.read_text(encoding="utf-8", errors="replace"))]
    if suffix == ".pdf":
        if PdfReader is None:
            raise RuntimeError("PDF support needs pypdf. Install requirements.txt first.")
        reader = PdfReader(str(path))
        return [(str(index + 1), page.extract_text() or "") for index, page in enumerate(reader.pages)]
    return []


def chunks(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    result = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + CHUNK_CHARS // 2:
                end = boundary
        result.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(start + 1, end - CHUNK_OVERLAP)
    return result


def ingest(paths: list[Path]) -> int:
    conn = connect()
    added = 0
    for path in paths:
        if not path.is_file():
            print(f"Skipping missing file: {path}", file=sys.stderr)
            continue
        pages = extract_text(path)
        if not pages:
            print(f"Skipping unsupported file: {path}", file=sys.stderr)
            continue
        conn.execute("DELETE FROM passages WHERE source = ?", (str(path.resolve()),))
        for page, text in pages:
            for piece in chunks(text):
                conn.execute(
                    "INSERT INTO passages(source, page, content) VALUES (?, ?, ?)",
                    (str(path.resolve()), page, piece),
                )
                added += 1
    conn.commit()
    conn.close()
    return added


def search(query: str, limit: int = 5) -> list[tuple[str, str, str]]:
    terms = re.findall(r"[\w'-]+", query)
    if not terms:
        return []
    # Quote terms so user punctuation cannot alter FTS query syntax.
    fts_query = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms[:12])
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT source, page, snippet(passages, 2, '[', ']', ' … ', 18) "
            "FROM passages WHERE passages MATCH ? ORDER BY rank LIMIT ?",
            (fts_query, limit),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return []
        raise
    finally:
        conn.close()
    return [(str(source), str(page), str(text)) for source, page, text in rows]


def api_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def loaded_model_id() -> str:
    request = urllib.request.Request(f"{BASE_URL}/models", headers=api_headers())
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            models = json.loads(response.read().decode("utf-8")).get("data", [])
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Could not list models from {BASE_URL}. Start Unsloth and set UNSLOTH_API_KEY "
            "to an API key created in Unsloth Settings → API."
        ) from exc
    if not models:
        raise RuntimeError("Unsloth returned no models. Load a model in Studio, then retry.")
    return next((model["id"] for model in models if model.get("loaded")), models[0]["id"])


def ask_model(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": MODEL or loaded_model_id(),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a careful local study assistant. Answer from the supplied course excerpts. "
                        "Cite supporting sources using the supplied labels. If the excerpts do not support "
                        "an answer, say so and ask the learner what topic to search next. Explain concepts "
                        "clearly and encourage understanding rather than merely giving memorization cues."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 500,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}/chat/completions", data=payload, headers=api_headers(), method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError("Unsloth rejected the API key. Create one in Unsloth Settings → API.") from exc
        raise RuntimeError(f"Unsloth API returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach Unsloth API at {BASE_URL}. Start Unsloth Studio, load a model, "
            "and set UNSLOTH_BASE_URL to its OpenAI-compatible API URL."
        ) from exc
    return result["choices"][0]["message"]["content"]


def generate_response(
    task: str, question: str, limit: int, topic: str | None = None
) -> dict[str, object]:
    search_text = topic or question
    passages = search(search_text, limit)
    if not passages:
        return {
            "answer": "No matching course passages found. Run the ingest command first or try different keywords.",
            "sources": [],
        }
    context = "\n\n".join(
        f"[{index}] Source: {Path(source).name}"
        f"{', page ' + page if page else ''}\n{text}"
        for index, (source, page, text) in enumerate(passages, start=1)
    )
    instructions = {
        "ask": f"Answer this study question and cite excerpt labels like [1]: {question}",
        "quiz": f"Create three short questions about this topic using only the excerpts. Do not include answers yet. Topic: {question}",
        "grade": f"Give constructive feedback on this learner answer about {search_text!r} using only the excerpts. State what is correct, what to improve, and a short model answer. Learner answer: {question}",
    }
    answer = ask_model(f"TASK: {instructions[task]}\n\nCOURSE EXCERPTS:\n{context}")
    sources = [
        {
            "index": index,
            "path": source,
            "name": Path(source).name,
            "page": page,
        }
        for index, (source, page, _) in enumerate(passages, start=1)
    ]
    return {"answer": answer, "sources": sources}


def respond(task: str, question: str, limit: int, topic: str | None = None) -> None:
    result = generate_response(task, question, limit, topic)
    print(result["answer"])
    sources = result["sources"]
    if sources:
        print("\nSources used:")
        for source in sources:
            page = source["page"]
            print(f"  [{source['index']}] {source['path']}{', page ' + page if page else ''}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local, source-grounded study assistant")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("save-key", help="Save the Unsloth key in the Linux desktop keyring")
    ingest_parser = subparsers.add_parser("ingest", help="Index TXT, Markdown and PDF course documents")
    ingest_parser.add_argument("paths", nargs="*", type=Path, help="Files/folders; defaults to ./documents")
    for task in ("ask", "quiz", "grade"):
        task_parser = subparsers.add_parser(task, help={"ask": "Ask a course question", "quiz": "Generate a short quiz", "grade": "Give feedback on an answer"}[task])
        task_parser.add_argument("text", help="Question, quiz topic, or learner answer")
        task_parser.add_argument("--limit", type=int, default=5, help="Number of retrieved passages (default: 5)")
        task_parser.add_argument("--topic", help="Topic to retrieve for; especially useful when grading an answer")
    args = parser.parse_args()

    if args.command == "save-key":
        save_api_key()
        return
    if args.command == "ingest":
        paths = args.paths or [DOCS_DIR]
        files = [path for item in paths for path in (item.rglob("*") if item.is_dir() else [item])]
        count = ingest(files)
        print(f"Indexed {count} passages into {DB_PATH}")
        return
    respond(args.command, args.text, args.limit, getattr(args, "topic", None))


if __name__ == "__main__":
    main()

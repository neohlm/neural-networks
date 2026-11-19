from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import study_assistant as assistant


MAX_JSON_BYTES = 1_000_000
MAX_FILE_BYTES = 20 * 1024 * 1024
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}

PAGE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local Study Assistant</title>
<style>
:root{
  color-scheme:dark;
  --void:#04050c;
  --glass:rgba(14,20,46,.78);
  --glass-soft:rgba(20,28,62,.82);
  --line:rgba(177,140,255,.24);
  --line-bright:rgba(189,148,255,.62);
  --ink:#e8edff;
  --dim:#a3adce;
  --faint:#7480a8;
  --purple:#bd94ff;
  --magenta:#ec8bff;
  --amber:#ffcb74;
  --green:#6dffb3;
  --red:#ff948b;
  --on-accent:#04050c;
  --body-glow:
    radial-gradient(ellipse 70% 50% at 85% -5%,rgba(189,148,255,.2),transparent 60%),
    radial-gradient(ellipse 55% 45% at -5% 35%,rgba(189,148,255,.13),transparent 60%),
    radial-gradient(ellipse 60% 40% at 50% 110%,rgba(236,139,255,.07),transparent 60%);
}
*{box-sizing:border-box}
html{min-height:100%;scroll-behavior:smooth}
body{margin:0;min-height:100vh;background-color:var(--void);background-image:var(--body-glow);background-attachment:fixed;color:var(--ink);font:15px/1.6 "Sora","Segoe UI",system-ui,sans-serif}
::selection{background:rgba(189,148,255,.38);color:#fff}
main{position:relative;z-index:1;max-width:940px;margin:0 auto;padding:34px 22px 60px}
header{display:flex;align-items:center;gap:15px;margin-bottom:26px;padding:12px 0 18px;border-bottom:1px solid var(--line)}
.mark{position:relative;width:46px;height:46px;flex:none;display:grid;place-items:center}
.mark-orbit{position:absolute;inset:4px;border:1px solid rgba(189,148,255,.72);border-left-color:rgba(189,148,255,.16);border-radius:50%;box-shadow:0 0 16px rgba(189,148,255,.13);animation:orbit-spin 7s linear infinite}
.mark-orbit::before{content:"";position:absolute;inset:5px;border:1px solid rgba(236,139,255,.22);border-radius:50%}
.mark-satellite{position:absolute;top:1px;left:50%;width:6px;height:6px;border-radius:50%;background:var(--magenta);box-shadow:0 0 10px var(--magenta);transform:translateX(-50%)}
.mark-core{width:13px;height:13px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#fff 0%,#e6d4ff 18%,var(--purple) 52%,#7045c8 100%);box-shadow:0 0 12px rgba(189,148,255,.78),0 0 26px rgba(189,148,255,.28);animation:core-breathe 2.4s ease-in-out infinite}
@keyframes orbit-spin{to{transform:rotate(360deg)}}
@keyframes core-breathe{0%,100%{transform:scale(.88);box-shadow:0 0 9px rgba(189,148,255,.58),0 0 18px rgba(189,148,255,.2)}50%{transform:scale(1.12);box-shadow:0 0 16px rgba(189,148,255,.9),0 0 30px rgba(189,148,255,.36)}}
.mark+div{transform:translateX(2px)}
h1{font-family:"Chakra Petch","Segoe UI",system-ui,sans-serif;font-size:1.65rem;line-height:1.2;letter-spacing:.04em;margin:0;background:linear-gradient(100deg,#fff 0%,#e5d7ff 42%,var(--purple) 74%,var(--magenta) 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
header p{color:var(--dim);margin:5px 0 0;font-size:.94rem}
.panel{position:relative;background:var(--glass);border:1px solid var(--line);border-radius:3px;padding:20px;margin:16px 0;box-shadow:inset 0 1px 0 rgba(255,255,255,.025),0 18px 45px -35px rgba(0,0,0,.9);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}
.panel::before,.panel::after{content:"";position:absolute;width:13px;height:13px;pointer-events:none}
.panel::before{top:-1px;left:-1px;border-top:2px solid var(--purple);border-left:2px solid var(--purple)}
.panel::after{right:-1px;bottom:-1px;border-right:2px solid var(--purple);border-bottom:2px solid var(--purple)}
.panel h2{font-family:"Chakra Petch","Segoe UI",system-ui,sans-serif;font-size:.94rem;letter-spacing:.14em;text-transform:uppercase;color:var(--purple);margin:0 0 12px}
small,.muted{color:var(--dim)}
.status{font-size:.9rem;color:var(--dim);word-break:break-word}
.row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
button,.button{border:1px solid var(--line-bright);border-radius:2px;padding:9px 15px;font:600 .83rem/1.4 "Chakra Petch","Segoe UI",system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;cursor:pointer;background:rgba(189,148,255,.2);color:var(--purple);transition:background .2s,border-color .2s,box-shadow .2s,transform .2s}
button:hover,.button:hover{background:rgba(189,148,255,.24);border-color:var(--purple);box-shadow:0 0 18px rgba(189,148,255,.24);transform:translateY(-1px)}
button.secondary{border-color:rgba(169,139,255,.42);background:rgba(189,148,255,.12);color:#c7b5ff}
button.secondary:hover{border-color:var(--magenta);background:rgba(189,148,255,.2);box-shadow:0 0 18px rgba(189,148,255,.24)}
button:disabled{opacity:.55;cursor:wait;transform:none;box-shadow:none}
input[type=file]{max-width:100%;font:inherit;color:var(--dim)}
input[type=file]::file-selector-button{margin-right:8px;padding:8px 11px;border:1px solid var(--line);border-radius:2px;background:var(--glass-soft);color:var(--ink);font:500 .82rem "Chakra Petch","Segoe UI",system-ui,sans-serif;cursor:pointer}
select,input[type=text],textarea{font:inherit;border:1px solid var(--line);border-radius:2px;padding:10px 12px;background:rgba(5,8,21,.82);color:var(--ink)}
select:focus-visible,input[type=text]:focus-visible,textarea:focus-visible,button:focus-visible,input[type=file]:focus-visible{outline:2px solid var(--purple);outline-offset:3px}
textarea{width:100%;min-height:110px;resize:vertical}
label{font:500 .79rem "Chakra Petch","Segoe UI",system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);display:block;margin-bottom:6px}
.grid{display:grid;grid-template-columns:1fr auto;gap:14px;align-items:end}
.task-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.docs{margin:12px 0 0;padding:0;list-style:none;display:flex;gap:7px;flex-wrap:wrap}
.docs li{display:flex;align-items:center;gap:8px;background:rgba(189,148,255,.08);border:1px solid var(--line);border-radius:2px;padding:4px 8px 4px 10px;font:.76rem "IBM Plex Mono",ui-monospace,monospace;color:var(--dim);overflow-wrap:anywhere}
.docs li span{min-width:0;overflow-wrap:anywhere}
.docs .remove-file{border-color:rgba(255,148,139,.38);background:rgba(255,148,139,.08);color:#ffb3ab;padding:3px 7px;font:500 .66rem "Chakra Petch","Segoe UI",system-ui,sans-serif;letter-spacing:.03em;text-transform:none}
.docs .remove-file:hover{border-color:var(--red);background:rgba(255,148,139,.18);box-shadow:0 0 12px rgba(255,148,139,.12)}
#notice{min-height:1.5em;margin:10px 0 0;color:var(--dim)}
#notice.error{color:var(--red)}
#library-notice.error{color:var(--red)}
.turn{padding:18px 0;border-bottom:1px solid var(--line)}
.turn:last-child{border-bottom:0}
.question{font-weight:650;color:#e1d6ff;margin:0 0 12px}
.answer{white-space:pre-wrap;margin:0;color:var(--ink)}
.sources{margin-top:14px;border-top:1px solid var(--line);padding-top:10px}
.sources summary{color:var(--purple);font:500 .78rem "Chakra Petch","Segoe UI",system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;cursor:pointer}
.sources ul{margin:8px 0 0;padding-left:22px;color:var(--dim);font-size:.88rem}
#conversation:empty{display:none}
footer{text-align:center;color:var(--faint);font: .7rem "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.05em;margin-top:22px}
:focus-visible{outline:2px solid var(--purple);outline-offset:3px}
@media(max-width:620px){main{padding:22px 14px 44px}.grid,.task-grid{grid-template-columns:1fr}.panel{padding:16px}.row>*{max-width:100%}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
</style>
</head>
<body>
<main>
<header>
  <div class="mark" aria-hidden="true">
    <span class="mark-orbit"><span class="mark-satellite"></span></span>
    <span class="mark-core"></span>
  </div>
  <div><h1>Local Study Assistant</h1><p>Ask questions grounded in your course notes.</p></div>
</header>

<section class="panel" aria-labelledby="library-title">
  <h2 id="library-title">Your study files</h2>
  <div class="row">
    <input id="file-input" type="file" accept=".pdf,.txt,.md" multiple aria-label="Choose study files">
    <button id="upload-button" class="secondary" type="button">Add files</button>
    <button id="index-button" type="button">Index files</button>
    <button id="model-button" class="secondary" type="button">Check model</button>
  </div>
  <ul id="documents" class="docs" aria-label="Study files"></ul>
  <p id="library-notice" class="status" aria-live="polite"></p>
</section>

<section class="panel" aria-labelledby="prompt-title">
  <h2 id="prompt-title">Study with your notes</h2>
  <form id="ask-form">
    <div class="task-grid">
      <div><label for="task">What would you like to do?</label>
        <select id="task"><option value="ask">Ask a question</option><option value="quiz">Make a quiz</option><option value="grade">Get feedback on my answer</option></select>
      </div>
      <div id="topic-wrap" hidden><label for="topic">Topic (optional)</label><input id="topic" type="text" placeholder="For example, gradient descent"></div>
    </div>
    <label id="text-label" for="prompt">Your question</label>
    <textarea id="prompt" maxlength="4000" required placeholder="For example, what is gradient descent?"></textarea>
    <div class="grid" style="margin-top:12px">
      <div><label for="limit">Number of note excerpts to use</label>
        <select id="limit"><option value="3">3 excerpts</option><option value="5" selected>5 excerpts</option><option value="8">8 excerpts</option></select>
      </div>
      <button id="send-button" type="submit">Get answer</button>
    </div>
  </form>
  <p id="notice" aria-live="polite"></p>
</section>

<section id="conversation" class="panel" aria-live="polite" aria-label="Study responses"></section>
<footer>Your files and questions stay on this computer. Unsloth Studio must be running to generate responses.</footer>
</main>
<script>
const byId = (id) => document.getElementById(id);
const task = byId("task");
const notice = byId("notice");
const libraryNotice = byId("library-notice");

function setNotice(element, message, isError) {
  element.textContent = message || "";
  element.classList.toggle("error", Boolean(isError));
}

async function readJson(response) {
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "The local app returned an error.");
  return data;
}

async function refreshStatus() {
  try {
    const info = await readJson(await fetch("/api/status"));
    const list = byId("documents");
    list.replaceChildren();
    if (!info.documents.length) {
      const item = document.createElement("li");
      item.textContent = "No study files added yet";
      list.append(item);
    } else {
      for (const documentName of info.documents) {
        const item = document.createElement("li");
        const name = document.createElement("span");
        name.textContent = documentName;
        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "remove-file";
        removeButton.textContent = "Remove";
        removeButton.setAttribute("aria-label", "Remove " + documentName);
        removeButton.addEventListener("click", async () => {
          if (!window.confirm("Remove " + documentName + " from study files? This also removes its indexed passages.")) return;
          removeButton.disabled = true;
          try {
            const result = await readJson(await fetch("/api/remove", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({name: documentName})
            }));
            setNotice(libraryNotice, "Removed " + result.filename + ".", false);
            await refreshStatus();
          } catch (error) {
            setNotice(libraryNotice, error.message, true);
            removeButton.disabled = false;
          }
        });
        item.append(name, removeButton);
        list.append(item);
      }
    }
  } catch (error) {
    // Keep the setup status area blank; document actions show errors where needed.
  }
}

task.addEventListener("change", () => {
  const grade = task.value === "grade";
  byId("topic-wrap").hidden = !grade;
  byId("text-label").textContent = grade ? "Your answer" : task.value === "quiz" ? "Quiz topic" : "Your question";
  byId("prompt").placeholder = grade ? "Type the answer you want feedback on…" :
    task.value === "quiz" ? "For example, activation functions" : "For example, what is gradient descent?";
  byId("send-button").textContent = task.value === "quiz" ? "Make quiz" : grade ? "Get feedback" : "Get answer";
});

byId("upload-button").addEventListener("click", async () => {
  const files = Array.from(byId("file-input").files || []);
  if (!files.length) {
    setNotice(libraryNotice, "Choose one or more PDF, TXT, or Markdown files first.", true);
    return;
  }
  byId("upload-button").disabled = true;
  try {
    for (const file of files) {
      const response = await fetch("/api/upload", {
        method: "POST",
        headers: {"Content-Type": "application/octet-stream", "X-Filename": encodeURIComponent(file.name)},
        body: file
      });
      const result = await readJson(response);
      setNotice(libraryNotice, "Added " + result.filename + ".", false);
    }
    byId("file-input").value = "";
    await refreshStatus();
  } catch (error) {
    setNotice(libraryNotice, error.message, true);
  } finally {
    byId("upload-button").disabled = false;
  }
});

byId("index-button").addEventListener("click", async () => {
  byId("index-button").disabled = true;
  setNotice(libraryNotice, "Reading and indexing your files…", false);
  try {
    const result = await readJson(await fetch("/api/ingest", {method: "POST"}));
    setNotice(libraryNotice, "Indexed " + result.passages + " passages from " + result.files + " file(s).", false);
  } catch (error) {
    setNotice(libraryNotice, error.message, true);
  } finally {
    byId("index-button").disabled = false;
  }
});

byId("model-button").addEventListener("click", async () => {
  byId("model-button").disabled = true;
  setNotice(libraryNotice, "Checking Unsloth and the loaded model…", false);
  try {
    const result = await readJson(await fetch("/api/model", {method: "POST"}));
    setNotice(libraryNotice, "Connected to model: " + result.model, false);
  } catch (error) {
    setNotice(libraryNotice, error.message, true);
  } finally {
    byId("model-button").disabled = false;
  }
});

function addTurn(question, data) {
  const turn = document.createElement("article");
  turn.className = "turn";
  const questionNode = document.createElement("p");
  questionNode.className = "question";
  questionNode.textContent = question;
  const answerNode = document.createElement("p");
  answerNode.className = "answer";
  answerNode.textContent = data.answer;
  turn.append(questionNode, answerNode);
  if (data.sources && data.sources.length) {
    const details = document.createElement("details");
    details.className = "sources";
    const summary = document.createElement("summary");
    summary.textContent = "Sources used (" + data.sources.length + ")";
    const list = document.createElement("ul");
    for (const source of data.sources) {
      const item = document.createElement("li");
      item.textContent = "[" + source.index + "] " + source.name + (source.page ? ", page " + source.page : "");
      list.append(item);
    }
    details.append(summary, list);
    turn.append(details);
  }
  byId("conversation").prepend(turn);
}

byId("ask-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = byId("prompt").value.trim();
  if (!text) return;
  const button = byId("send-button");
  button.disabled = true;
  setNotice(notice, "Searching your notes and asking the local model…", false);
  try {
    const data = await readJson(await fetch("/api/respond", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        task: task.value,
        text: text,
        topic: byId("topic").value.trim(),
        limit: Number(byId("limit").value)
      })
    }));
    addTurn(text, data);
    byId("prompt").value = "";
    setNotice(notice, "", false);
  } catch (error) {
    setNotice(notice, error.message, true);
  } finally {
    button.disabled = false;
  }
});

refreshStatus();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalStudyAssistant/1.0"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _read_body(self, maximum: int) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Invalid request size.") from error
        if length < 0 or length > maximum:
            raise ValueError("Request is too large.")
        return self.rfile.read(length)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/api/status":
            files = sorted(
                item.relative_to(assistant.DOCS_DIR).as_posix()
                for item in assistant.DOCS_DIR.rglob("*")
                if item.is_file() and item.suffix.lower() in SUPPORTED_SUFFIXES
            ) if assistant.DOCS_DIR.exists() else []
            self._json(200, {
                "documents": files,
            })
            return
        self._json(404, {"error": "Not found."})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        try:
            if path == "/api/upload":
                self._upload()
            elif path == "/api/remove":
                self._remove()
            elif path == "/api/ingest":
                self._ingest()
            elif path == "/api/model":
                self._model()
            elif path == "/api/respond":
                self._respond()
            else:
                self._json(404, {"error": "Not found."})
        except ValueError as error:
            self._json(400, {"error": str(error)})
        except Exception as error:
            message = str(error).replace(assistant.BASE_URL, "the configured local model service")
            self._json(500, {"error": message or "The local assistant encountered an error."})

    def _upload(self) -> None:
        body = self._read_body(MAX_FILE_BYTES)
        raw_name = unquote(self.headers.get("X-Filename", "")).replace("\\", "/")
        filename = raw_name.rsplit("/", 1)[-1].strip()
        suffix = Path(filename).suffix.lower()
        if not filename or filename in {".", ".."} or suffix not in SUPPORTED_SUFFIXES:
            raise ValueError("Choose a PDF, TXT, or Markdown file.")
        if not body:
            raise ValueError("The selected file is empty.")
        assistant.DOCS_DIR.mkdir(parents=True, exist_ok=True)
        target = assistant.DOCS_DIR / filename
        if target.is_symlink():
            raise ValueError("That filename is already used by a symbolic link.")
        if target.exists():
            stem = Path(filename).stem
            extension = Path(filename).suffix
            number = 2
            while target.exists():
                target = assistant.DOCS_DIR / f"{stem} ({number}){extension}"
                number += 1
        target.write_bytes(body)
        self._json(201, {"filename": target.name})

    def _remove(self) -> None:
        raw = self._read_body(MAX_JSON_BYTES)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Invalid request data.") from error
        if not isinstance(payload, dict) or not isinstance(payload.get("name"), str):
            raise ValueError("Choose a study file to remove.")

        relative = Path(payload["name"])
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ValueError("Invalid study file name.")
        candidate = assistant.DOCS_DIR / relative
        if candidate.is_symlink():
            raise ValueError("Symbolic links cannot be removed from the study file list.")
        root = assistant.DOCS_DIR.resolve()
        resolved = candidate.resolve()
        if not resolved.is_relative_to(root):
            raise ValueError("That file is outside the study files folder.")
        if resolved.suffix.lower() not in SUPPORTED_SUFFIXES or not resolved.is_file():
            raise ValueError("That study file no longer exists.")

        resolved.unlink()
        conn = assistant.connect()
        try:
            conn.execute("DELETE FROM passages WHERE source = ?", (str(resolved),))
            conn.commit()
        finally:
            conn.close()
        self._json(200, {"filename": relative.as_posix()})

    def _ingest(self) -> None:
        if self._read_body(MAX_JSON_BYTES):
            raise ValueError("This request should not include a body.")
        files = sorted(
            item for item in assistant.DOCS_DIR.rglob("*")
            if item.is_file() and item.suffix.lower() in SUPPORTED_SUFFIXES
        ) if assistant.DOCS_DIR.exists() else []
        passages = assistant.ingest(files)
        self._json(200, {"files": len(files), "passages": passages})

    def _model(self) -> None:
        if self._read_body(MAX_JSON_BYTES):
            raise ValueError("This request should not include a body.")
        self._json(200, {"model": assistant.loaded_model_id()})

    def _respond(self) -> None:
        raw = self._read_body(MAX_JSON_BYTES)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Invalid request data.") from error
        if not isinstance(payload, dict):
            raise ValueError("Invalid request data.")
        task = payload.get("task")
        text = payload.get("text")
        topic = payload.get("topic", "")
        if task not in {"ask", "quiz", "grade"}:
            raise ValueError("Choose ask, quiz, or grade.")
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            raise ValueError("Enter text up to 4,000 characters.")
        if not isinstance(topic, str) or len(topic) > 500:
            raise ValueError("The topic must be 500 characters or fewer.")
        try:
            limit = int(payload.get("limit", 5))
        except (TypeError, ValueError) as error:
            raise ValueError("Choose between 1 and 10 excerpts.") from error
        if not 1 <= limit <= 10:
            raise ValueError("Choose between 1 and 10 excerpts.")
        result = assistant.generate_response(task, text.strip(), limit, topic.strip() or None)
        self._json(200, result)

    def log_message(self, format: str, *args: object) -> None:
        super().log_message(format, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local study assistant browser interface")
    parser.add_argument("--port", type=int, default=8765, help="Local web server port (default: 8765)")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Open http://127.0.0.1:{args.port} in your browser.")
    print("Keep this terminal open while using the assistant. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local study assistant.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

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
*{box-sizing:border-box}
:root{color-scheme:dark;--page:#101114;--surface:#191a1d;--surface-2:#222327;--line:#303136;--ink:#ececf0;--muted:#a3a4aa;--soft:#777980;--accent:#a8c7fa;--accent-ink:#172033;--green:#a8d5b5;--red:#ffb4ab}
html,body{min-height:100%;margin:0}
body{background:var(--page);color:var(--ink);font:14px/1.55 "Segoe UI",system-ui,sans-serif}
button,input,select,textarea{font:inherit}button{cursor:pointer;color:inherit}
main{min-height:100vh;display:grid;grid-template-rows:64px 1fr}
header{height:64px;display:flex;align-items:center;gap:14px;padding:0 22px;border-bottom:1px solid var(--line);background:rgba(25,26,29,.94)}
.mark{display:grid;place-items:center;width:34px;height:34px;border-radius:11px;background:#283142;color:var(--accent);font-size:19px;font-weight:700}
.mark::after{content:"✦"}
.mark-orbit,.mark-satellite,.mark-core{display:none}
h1{font-size:1.05rem;line-height:1.2;margin:0;font-weight:600;letter-spacing:0}
header p{margin:2px 0 0;color:var(--muted);font-size:.78rem}
.workspace{min-height:0;display:grid;grid-template-columns:270px minmax(360px,1fr) 280px}
.panel{min-width:0;padding:18px;background:var(--surface);border:0;border-right:1px solid var(--line);border-radius:0;margin:0;box-shadow:none}
.panel::before,.panel::after{display:none}
.panel h2{font-size:.81rem;line-height:1.3;font-weight:600;letter-spacing:.02em;text-transform:none;color:var(--ink);margin:0}
small,.muted,.status{color:var(--muted)}
.status{font-size:.8rem;word-break:break-word;min-height:1.4em}
.row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
button,.button{border:1px solid var(--line);border-radius:999px;padding:8px 13px;font-size:.82rem;font-weight:550;background:var(--surface-2);color:var(--ink);transition:background .15s,border-color .15s}
button:hover,.button:hover{background:#303137;border-color:#51535a}
button.secondary{background:transparent;color:var(--ink);border-color:var(--line)}
button:disabled{opacity:.55;cursor:wait}
input[type=file]{max-width:100%;font:inherit;color:var(--muted);font-size:.78rem}
input[type=file]::file-selector-button{margin:0 0 8px;padding:8px 11px;border:1px solid var(--line);border-radius:999px;background:var(--surface-2);color:var(--ink);cursor:pointer}
select,input[type=text],textarea{font:inherit;border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:#121316;color:var(--ink)}
select:focus-visible,input[type=text]:focus-visible,textarea:focus-visible,button:focus-visible,input[type=file]:focus-visible{outline:2px solid var(--purple);outline-offset:3px}
textarea{width:100%;min-height:110px;resize:vertical}
label{font-size:.78rem;color:var(--muted);display:block;margin-bottom:6px}
.grid{display:flex;justify-content:space-between;gap:12px;align-items:center}
.task-grid{display:grid;grid-template-columns:1fr;gap:12px;margin:16px 0}
.docs{margin:14px 0 0;padding:0;list-style:none;display:grid;gap:5px}
.docs li{display:flex;align-items:center;gap:9px;background:transparent;border:0;border-radius:9px;padding:9px;color:var(--muted);font-size:.82rem;overflow-wrap:anywhere}
.docs li::before{content:"▤";color:var(--accent);flex:none}
.docs li span{min-width:0;overflow-wrap:anywhere;flex:1}
.docs .remove-file{border-color:transparent;background:transparent;color:var(--muted);padding:4px 7px;font-size:.72rem}
#notice{min-height:1.5em;margin:10px 0 0;color:var(--muted)}
#notice.error{color:var(--red)}
#library-notice.error{color:var(--red)}
.turn{max-width:760px;padding:22px 0;border-bottom:1px solid var(--line)}
.turn:last-child{border-bottom:0}
.question{font-weight:600;color:var(--ink);margin:0 0 12px}
.answer{white-space:pre-wrap;margin:0;color:var(--ink)}
.sources{margin-top:14px;border-top:1px solid var(--line);padding-top:10px}
.sources summary{color:var(--accent);font-size:.78rem;cursor:pointer}
.sources ul{margin:8px 0 0;padding-left:22px;color:var(--dim);font-size:.88rem}
footer{text-align:center;color:var(--soft);font-size:.72rem;margin:14px 0 0}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.sources-panel{padding:20px 14px}
.sources-panel .row{margin-top:15px;display:grid}
.sources-panel .file-actions{display:flex;gap:7px}
.sources-panel .file-actions button{flex:1}
.chat-panel{position:relative;display:flex;flex-direction:column;align-items:center;min-height:calc(100vh - 64px);padding:0 28px 20px;border-right:1px solid var(--line);background:#131416}
.chat-head{width:100%;max-width:760px;display:flex;align-items:center;justify-content:space-between;padding:17px 0;border-bottom:1px solid var(--line)}
.chat-head h2{font-size:.92rem;font-weight:600}
#conversation{width:100%;max-width:760px;flex:1;overflow:auto;padding:8px 4px 18px;background:transparent}
#conversation:empty{display:block}
.welcome{min-height:48vh;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;color:var(--muted)}
.welcome .welcome-icon{font-size:2.4rem;color:var(--accent);margin-bottom:12px}
.welcome h2{font-size:1.55rem;font-weight:500;color:var(--ink);margin:0 0 6px}
.welcome p{max-width:420px;margin:0}
.composer{width:100%;max-width:760px;border:1px solid #484a51;border-radius:22px;background:var(--surface);padding:13px 15px 10px;box-shadow:0 8px 26px #0003}
.composer textarea{display:block;border:0;background:transparent;min-height:56px;max-height:180px;resize:vertical;padding:4px 3px;outline:none}
.composer textarea:focus-visible{outline:none}
.composer-tools{display:flex;justify-content:space-between;align-items:center;gap:10px;padding-top:8px;border-top:1px solid var(--line)}
.composer-tools select{padding:6px 10px;border-radius:999px;font-size:.78rem}
.send-button{background:var(--accent);color:var(--accent-ink);border:0;font-weight:650}
.send-button:hover{background:#c2d9ff}
.studio-panel{padding:20px 16px;border-right:0}
.studio-panel .panel-title-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
.studio-card{margin-top:12px;padding:13px;border:1px solid var(--line);border-radius:12px;background:var(--surface-2)}
.studio-card h3{font-size:.84rem;margin:0 0 5px}
.studio-card p{font-size:.77rem;color:var(--muted);margin:0}
.studio-panel select,.studio-panel input{width:100%}
.model-check{width:100%;margin-top:12px}
@media(max-width:1000px){.workspace{grid-template-columns:230px minmax(300px,1fr)}.studio-panel{display:none}}
@media(max-width:680px){main{grid-template-rows:58px 1fr}header{height:58px;padding:0 14px}.workspace{grid-template-columns:1fr;grid-template-rows:auto 1fr}.sources-panel{border-right:0;border-bottom:1px solid var(--line);padding:12px 14px}.sources-panel .row{display:flex;margin-top:9px}.sources-panel .row input{min-width:0;flex:1}.sources-panel .file-actions{width:100%}.sources-panel h2{font-size:.82rem}.docs{grid-template-columns:1fr 1fr;max-height:108px;overflow:auto}.docs li{padding:5px}.chat-panel{min-height:calc(100vh - 58px);padding:0 14px 14px;border:0}.welcome{min-height:32vh}.grid{align-items:end}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
</style>
</head>
<body>
<main>
<header>
  <div class="mark" aria-hidden="true"></div>
  <div><h1>Study notebook</h1><p>Local Study Assistant</p></div>
</header>
<div class="workspace">
  <aside class="panel sources-panel" aria-labelledby="library-title">
    <h2 id="library-title">Sources</h2>
    <p class="muted" style="font-size:.78rem;margin:5px 0 0">Add your course notes to start a notebook.</p>
    <div class="row">
      <input id="file-input" type="file" accept=".pdf,.txt,.md" multiple aria-label="Choose study files">
      <div class="file-actions"><button id="upload-button" class="secondary" type="button">Add files</button><button id="index-button" type="button">Index</button></div>
    </div>
    <ul id="documents" class="docs" aria-label="Study files"></ul>
    <p id="library-notice" class="status" aria-live="polite"></p>
  </aside>

  <section class="chat-panel" aria-labelledby="chat-title">
    <div class="chat-head"><h2 id="chat-title">Notebook chat</h2><span class="muted" style="font-size:.76rem">Grounded in your sources</span></div>
    <section id="conversation" aria-live="polite" aria-label="Study responses">
      <div class="welcome"><div class="welcome-icon" aria-hidden="true">✦</div><h2>What would you like to learn?</h2><p>Ask a question about your sources, make a quiz, or get feedback on an answer.</p></div>
    </section>
    <form id="ask-form" class="composer">
      <div class="task-grid">
        <div><label for="task">Study mode</label>
          <select id="task"><option value="ask">Ask a question</option><option value="quiz">Make a quiz</option><option value="grade">Get feedback on my answer</option></select>
        </div>
        <div id="topic-wrap" hidden><label for="topic">Topic (optional)</label><input id="topic" type="text" placeholder="For example, gradient descent"></div>
      </div>
      <label id="text-label" for="prompt">Your question</label>
      <textarea id="prompt" maxlength="4000" required placeholder="Ask a question about your course materials…"></textarea>
      <p id="notice" aria-live="polite"></p>
      <div class="composer-tools"><label for="limit" style="margin:0">Sources to use</label>
        <select id="limit" aria-label="Number of note excerpts to use"><option value="3">3 excerpts</option><option value="5" selected>5 excerpts</option><option value="8">8 excerpts</option></select>
        <button id="send-button" class="send-button" type="submit">Ask</button>
      </div>
    </form>
    <footer>Your files and questions stay on this computer. Unsloth Studio must be running to generate responses.</footer>
  </section>

  <aside class="panel studio-panel" aria-labelledby="studio-title">
    <div class="panel-title-row"><h2 id="studio-title">Studio</h2><span aria-hidden="true" style="color:var(--accent)">✦</span></div>
    <p class="muted" style="font-size:.8rem;margin:0">Turn your sources into active study practice.</p>
    <div class="studio-card"><h3>Make a quiz</h3><p>Generate practice questions from the selected topic and your indexed notes.</p></div>
    <div class="studio-card"><h3>Check an answer</h3><p>Write what you know and get source based feedback.</p></div>
    <label for="studio-task" style="margin-top:18px">Choose an activity</label>
    <select id="studio-task"><option value="ask">Ask about sources</option><option value="quiz">Make a quiz</option><option value="grade">Get answer feedback</option></select>
    <button id="model-button" class="secondary model-check" type="button">Check local model</button>
    <p class="status" style="margin-top:8px">The model runs locally through Unsloth Studio.</p>
  </aside>
</div>
</main>
<script>
const byId = (id) => document.getElementById(id);
const task = byId("task");
const notice = byId("notice");
const libraryNotice = byId("library-notice");
const studioTask = byId("studio-task");

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
  studioTask.value = task.value;
  const grade = task.value === "grade";
  byId("topic-wrap").hidden = !grade;
  byId("text-label").textContent = grade ? "Your answer" : task.value === "quiz" ? "Quiz topic" : "Your question";
  byId("prompt").placeholder = grade ? "Type the answer you want feedback on…" :
    task.value === "quiz" ? "For example, activation functions" : "For example, what is gradient descent?";
  byId("send-button").textContent = task.value === "quiz" ? "Make quiz" : grade ? "Get feedback" : "Get answer";
});

studioTask.addEventListener("change", () => {
  task.value = studioTask.value;
  task.dispatchEvent(new Event("change"));
  byId("prompt").focus();
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
  const welcome = document.querySelector(".welcome");
  if (welcome) welcome.remove();
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

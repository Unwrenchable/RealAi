"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.RealAIChatPanel = void 0;
const vscode = __importStar(require("vscode"));
class RealAIChatPanel {
    /** Convenience accessor for extension.ts commands */
    static get instance() {
        return RealAIChatPanel.currentPanel;
    }
    get lastResponse() {
        return this._lastResponse;
    }
    static createOrShow(ctx, client) {
        if (RealAIChatPanel.currentPanel) {
            RealAIChatPanel.currentPanel.panel.reveal(vscode.ViewColumn.Beside);
            return;
        }
        const panel = vscode.window.createWebviewPanel('realaiChat', 'RealAI Chat', vscode.ViewColumn.Beside, {
            enableScripts: true,
            retainContextWhenHidden: true,
            localResourceRoots: [],
        });
        RealAIChatPanel.currentPanel = new RealAIChatPanel(panel, client, ctx);
    }
    constructor(panel, client, ctx) {
        /** Full conversation history */
        this.messages = [];
        this.isStreaming = false;
        /** Last full assistant response (for insert-into-editor) */
        this._lastResponse = '';
        /** Pending input that gets set when the webview is ready */
        this.pendingInput = '';
        this.panel = panel;
        this.client = client;
        this.ctx = ctx;
        this.panel.webview.html = this.getHtml();
        this.panel.onDidDispose(() => {
            RealAIChatPanel.currentPanel = undefined;
        });
        this.panel.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.command) {
                case 'chat':
                    await this.handleChat(msg.text);
                    break;
                case 'stream':
                    await this.handleStream(msg.text);
                    break;
                case 'clear':
                    this.messages = [];
                    this._lastResponse = '';
                    this.panel.webview.postMessage({ command: 'clear' });
                    break;
                case 'ready':
                    // Webview is ready — flush any pending input
                    if (this.pendingInput) {
                        const text = this.pendingInput;
                        this.pendingInput = '';
                        this.panel.webview.postMessage({ command: 'setInput', text });
                    }
                    break;
                case 'insertResponse':
                    // User clicked "Insert" button in the webview
                    vscode.commands.executeCommand('realai.insertResponse');
                    break;
                case 'openFile':
                    // User clicked a file reference
                    if (msg.path) {
                        const uri = vscode.Uri.file(msg.path);
                        vscode.window.showTextDocument(uri);
                    }
                    break;
            }
        });
    }
    /** Set the input text in the chat box (once webview is ready) */
    setInput(text) {
        if (this.panel.webview) {
            this.panel.webview.postMessage({ command: 'setInput', text });
        }
        else {
            this.pendingInput = text;
        }
    }
    /** Programmatically send a message */
    async sendMessage(text) {
        // Use streaming by default
        await this.handleStream(text);
    }
    // ==================== Non-streaming fallback ====================
    async handleChat(text) {
        this.messages.push({ role: 'user', content: text });
        this.appendMessage('user', text);
        try {
            const reply = await this.client.chatPrompt(text);
            this.messages.push({ role: 'assistant', content: reply });
            this._lastResponse = reply;
            this.appendMessage('assistant', reply);
        }
        catch (e) {
            this.appendMessage('error', `Error: ${e.message}`);
        }
    }
    // ==================== Streaming ====================
    async handleStream(text) {
        if (this.isStreaming)
            return;
        this.isStreaming = true;
        this.messages.push({ role: 'user', content: text });
        this.appendMessage('user', text);
        // Tell webview to show a streaming message placeholder
        this.panel.webview.postMessage({ command: 'streamStart' });
        let fullContent = '';
        const callbacks = {
            onToken: (token) => {
                fullContent += token;
                this.panel.webview.postMessage({ command: 'streamToken', token });
            },
            onDone: (_fullContent) => {
                this.isStreaming = false;
                this.messages.push({ role: 'assistant', content: fullContent });
                this._lastResponse = fullContent;
                this.panel.webview.postMessage({ command: 'streamEnd' });
            },
            onError: (error) => {
                this.isStreaming = false;
                this.appendMessage('error', `Error: ${error}`);
                this.panel.webview.postMessage({ command: 'streamEnd' });
            },
        };
        await this.client.streamChatPrompt(text, callbacks);
    }
    // ==================== Append a message to the webview ====================
    appendMessage(role, content) {
        this.panel.webview.postMessage({ command: 'append', role, content });
    }
    // ==================== Static helpers for extension.ts ====================
    static postActivity(text) {
        RealAIChatPanel.currentPanel?.panel.webview.postMessage({ command: 'activity', text });
    }
    // ==================== Webview HTML ====================
    getHtml() {
        return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #0d0d1a;
  --bg2: #13132a;
  --bg3: #1a1a3e;
  --border: #2a2a5a;
  --text: #e0e0ff;
  --text2: #9090cc;
  --accent: #7c5cfc;
  --user-bg: #1a1a5a;
  --ai-bg: #13132a;
  --error: #c62828;
  --code-bg: #0a0a14;
}
body {
  font-family: 'Segoe UI', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
header {
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  padding: 8px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.logo {
  font-size: 1rem;
  font-weight: 700;
}
.logo .accent { color: var(--accent); }
.header-actions { display: flex; gap: 6px; }
.btn {
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.75rem;
  background: var(--bg3);
  color: var(--text);
  transition: background 0.15s;
}
.btn:hover { background: var(--accent); color: #fff; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
#messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
#messages::-webkit-scrollbar { width: 5px; }
#messages::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
.message { display: flex; flex-direction: column; max-width: 92%; animation: fadeIn 0.15s ease; }
.message.user { align-self: flex-end; }
.message.assistant, .message.error { align-self: flex-start; }
.message-header {
  font-size: 0.68rem;
  color: var(--text2);
  margin-bottom: 2px;
  padding: 0 4px;
}
.message.user .message-header { text-align: right; }
.bubble {
  padding: 10px 14px;
  border-radius: 10px;
  line-height: 1.55;
  font-size: 0.88rem;
  word-break: break-word;
  white-space: pre-wrap;
}
.message.user .bubble {
  background: var(--user-bg);
  border: 1px solid #2a2a7a;
  border-bottom-right-radius: 3px;
}
.message.assistant .bubble {
  background: var(--ai-bg);
  border: 1px solid var(--border);
  border-bottom-left-radius: 3px;
}
.message.error .bubble {
  background: #2a1010;
  border: 1px solid var(--error);
  color: #ef9a9a;
}
.bubble code {
  background: var(--code-bg);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
  font-size: 0.82rem;
}
.bubble pre {
  background: var(--code-bg);
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 6px 0;
  font-size: 0.82rem;
}
.typing { display: inline-flex; gap: 3px; align-items: center; padding: 4px 0; }
.typing span {
  width: 6px; height: 6px;
  background: var(--text2);
  border-radius: 50%;
  animation: blink 1.2s infinite;
}
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%,80%,100% { opacity: 0.2; } 40% { opacity: 1; } }
@keyframes fadeIn { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: none; } }
#welcome {
  text-align: center;
  margin: auto;
  padding: 30px;
}
#welcome .icon { font-size: 2.5rem; margin-bottom: 10px; }
#welcome h2 { font-size: 1.2rem; margin-bottom: 6px; }
#welcome p { color: var(--text2); font-size: 0.85rem; margin-bottom: 14px; }
.input-area {
  background: var(--bg2);
  border-top: 1px solid var(--border);
  padding: 8px 12px;
  flex-shrink: 0;
}
.input-row { display: flex; gap: 8px; align-items: flex-end; }
#input {
  flex: 1;
  background: var(--bg3);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 0.88rem;
  resize: none;
  min-height: 38px;
  max-height: 140px;
  font-family: inherit;
  line-height: 1.5;
}
#input:focus { outline: none; border-color: var(--accent); }
#send-btn {
  width: 38px; height: 38px;
  border-radius: 8px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}
.hint {
  font-size: 0.7rem;
  color: var(--text2);
  margin-top: 4px;
}
.hint kbd {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 0 4px;
  font-size: 0.68rem;
  font-family: inherit;
}
.action-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--text2);
  padding: 2px 8px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.7rem;
  margin-left: 6px;
  transition: all 0.15s;
}
.action-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}
</style>
</head>
<body>
<header>
  <div class="logo">&#x1F916; Real<span class="accent">AI</span> <span style="font-size:0.7rem;color:var(--text2)">Chat</span></div>
  <div class="header-actions">
    <button class="btn" onclick="clearChat()">Clear</button>
  </div>
</header>

<div id="messages">
  <div id="welcome">
    <div class="icon">&#x1F916;</div>
    <h2>RealAI Chat</h2>
    <p>Ask questions about your code, get explanations, or just chat.</p>
  </div>
</div>

<div class="input-area">
  <div class="input-row">
    <textarea id="input" rows="1"
      placeholder="Ask RealAI anything&hellip;"
      onkeydown="handleKey(event)"
      oninput="autoResize(this)"></textarea>
    <button class="btn" id="send-btn" onclick="sendMessage()">&#x2191;</button>
  </div>
  <div class="hint">
    <kbd>Enter</kbd> to send &middot; <kbd>Shift+Enter</kbd> for new line &middot;
    <kbd>Ctrl+Shift+I</kbd> to insert response
  </div>
</div>

<script>
(function() {
  const vscode = acquireVsCodeApi();
  const messagesEl = document.getElementById('messages');
  const inputEl = document.getElementById('input');
  const sendBtn = document.getElementById('send-btn');
  let isStreaming = false;
  let streamMsgEl = null;

  // Tell the extension we're ready
  vscode.postMessage({ command: 'ready' });

  // ---- Input handling ----
  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
  }

  function sendMessage() {
    const text = inputEl.value.trim();
    if (!text || isStreaming) return;
    inputEl.value = '';
    inputEl.style.height = 'auto';
    removeWelcome();
    vscode.postMessage({ command: 'stream', text });
  }

  sendBtn.addEventListener('click', sendMessage);

  // ---- Clear ----
  function clearChat() {
    vscode.postMessage({ command: 'clear' });
  }

  // ---- Remove welcome message ----
  function removeWelcome() {
    const w = document.getElementById('welcome');
    if (w) w.remove();
  }

  // ---- Message rendering ----
  function appendMessage(role, content) {
    const div = document.createElement('div');
    div.className = 'message ' + role;

    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = role === 'user' ? 'You' : role === 'assistant' ? 'RealAI' : 'Error';
    div.appendChild(header);

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = formatContent(content);
    div.appendChild(bubble);

    // Add insert button for assistant messages
    if (role === 'assistant' && content) {
      const insertBtn = document.createElement('button');
      insertBtn.className = 'action-btn';
      insertBtn.textContent = 'Insert';
      insertBtn.title = 'Insert response into editor';
      insertBtn.onclick = () => vscode.postMessage({ command: 'insertResponse' });
      bubble.appendChild(insertBtn);
    }

    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function formatContent(text) {
    if (!text) return '';
    // Escape HTML first
    let s = String(text)
      .replace(/&/g, '&')
      .replace(/</g, '<')
      .replace(/>/g, '>');

    // Convert markdown-style ` ``;
        code `` ` blocks
    s = s.replace(/` ``(w * );
        n ? ([s, S] *  ?  : ) `` `/g, (_, lang, code) => {
      return '<pre><code>' + code.trim() + '</code></pre>';
    });

    // Convert inline ` : ;
        code `
    s = s.replace(/`([ ^ `]+)` / g, '<code>$1</code>']);
        // Convert double newlines to <br><br>
        s = s.replace(/\n\n/g, '</p><p>');
        s = s.replace(/\n/g, '<br>');
        s = '<p>' + s + '</p>';
        return s;
    }
}
exports.RealAIChatPanel = RealAIChatPanel;
// ---- Streaming ----
function streamStart() {
    isStreaming = true;
    sendBtn.disabled = true;
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.id = 'stream-msg';
    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = 'RealAI';
    div.appendChild(header);
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
    div.appendChild(bubble);
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    streamMsgEl = bubble;
}
function streamToken(token) {
    if (!streamMsgEl)
        return;
    // Replace typing indicator with the actual content
    if (streamMsgEl.querySelector('.typing')) {
        streamMsgEl.innerHTML = '';
    }
    streamMsgEl.innerHTML += formatContent(token);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}
function streamEnd() {
    isStreaming = false;
    sendBtn.disabled = false;
    streamMsgEl = null;
}
// ---- Set input programmatically ----
function setInput(text) {
    inputEl.value = text;
    inputEl.focus();
    autoResize(inputEl);
}
// ---- Message handling from extension ----
window.addEventListener('message', function (e) {
    const d = e.data;
    switch (d.command) {
        case 'append':
            removeWelcome();
            appendMessage(d.role, d.content);
            break;
        case 'streamStart':
            removeWelcome();
            streamStart();
            break;
        case 'streamToken':
            streamToken(d.token);
            break;
        case 'streamEnd':
            streamEnd();
            break;
        case 'clear':
            messagesEl.innerHTML = '';
            messagesEl.innerHTML =
                '<div id="welcome">' +
                    '<div class="icon">&#x1F916;</div>' +
                    '<h2>RealAI Chat</h2>' +
                    '<p>Ask questions about your code, get explanations, or just chat.</p>' +
                    '</div>';
            streamEnd();
            break;
        case 'setInput':
            setInput(d.text);
            break;
        case 'activity':
            console.log('[RealAI Activity]', d.text);
            break;
    }
});
();
/script>
    < /body>
    < /html>`;

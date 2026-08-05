"""
RealAI GUI Launcher

A graphical interface for configuring API keys and launching the RealAI API
server.  Runs on Windows, macOS, and Linux (requires tkinter, which ships with
the official Python installer on Windows and macOS).

Usage
-----
Run directly::

    python realai_gui.py

Build a Windows .exe::

    pip install pyinstaller
    pyinstaller realai_launcher.spec
    # Output: dist/RealAI.exe
"""

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
from typing import Callable, Dict, List, Optional
import urllib.request
import urllib.error
from copy import deepcopy

from realai import PROVIDER_ENV_VARS

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".realai")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "config.json")

#: Ordered list of providers shown in the UI.
#: ``env_var`` values are sourced from :data:`realai.PROVIDER_ENV_VARS`.
PROVIDERS = {
    "openai": {
        "label": "OpenAI",
        "placeholder": "sk-...",
        "help": "Get your key at https://platform.openai.com/api-keys",
        "env_var": PROVIDER_ENV_VARS["openai"],
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "placeholder": "sk-ant-...",
        "help": "Get your key at https://console.anthropic.com/",
        "env_var": PROVIDER_ENV_VARS["anthropic"],
    },
    "grok": {
        "label": "xAI / Grok",
        "placeholder": "xai-...",
        "help": "Get your key at https://console.x.ai/",
        "env_var": PROVIDER_ENV_VARS["grok"],
    },
    "gemini": {
        "label": "Google Gemini",
        "placeholder": "AIza...",
        "help": "Get your key at https://aistudio.google.com/app/apikey",
        "env_var": PROVIDER_ENV_VARS["gemini"],
    },
    "openrouter": {
        "label": "OpenRouter",
        "placeholder": "sk-or-v1-...",
        "help": "Get your key at https://openrouter.ai/keys",
        "env_var": PROVIDER_ENV_VARS["openrouter"],
    },
    "mistral": {
        "label": "Mistral AI",
        "placeholder": "...",
        "help": "Get your key at https://console.mistral.ai/api-keys",
        "env_var": PROVIDER_ENV_VARS["mistral"],
    },
    "together": {
        "label": "Together AI",
        "placeholder": "...",
        "help": "Get your key at https://api.together.xyz/settings/api-keys",
        "env_var": PROVIDER_ENV_VARS["together"],
    },
    "deepseek": {
        "label": "DeepSeek",
        "placeholder": "...",
        "help": "Get your key at https://platform.deepseek.com/api_keys",
        "env_var": PROVIDER_ENV_VARS["deepseek"],
    },
    "perplexity": {
        "label": "Perplexity AI",
        "placeholder": "pplx-...",
        "help": "Get your key at https://www.perplexity.ai/settings/api",
        "env_var": PROVIDER_ENV_VARS["perplexity"],
    },
}


def load_config() -> dict:
    """Load saved API keys from ``~/.realai/config.json``."""
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_config(config: dict) -> None:
    """Persist API keys to ``~/.realai/config.json``."""
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class RealAILauncher(tk.Tk):
    """Main GUI window for RealAI API key configuration and server control."""

    _HEADER_BG = "#1a1a2e"
    _HEADER_FG = "#e0e0ff"
    _HEADER_SUB = "#9090cc"
    _BTN_SAVE = "#2a7a4f"
    _BTN_START = "#1565c0"
    _BTN_STOP = "#c62828"
    _PAD = 14
    _API_BASE_URL = "http://localhost:8000"
    _DEFAULT_MODEL = "realai-2.0"
    _API_TIMEOUT = 30

    def __init__(self):
        super().__init__()
        self.title("RealAI v2.0 \u2014 API Key Setup")
        self.resizable(True, True)
        self._server_proc: Optional[subprocess.Popen] = None
        self._entries: Dict[str, tk.Entry] = {}
        self._chat_history: List[Dict[str, str]] = []
        self._build_ui()
        self._load_saved_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        pad = self._PAD

        # Set a minimum size so the Save/Start buttons are always reachable.
        self.minsize(620, 560)

        # Header bar
        header = tk.Frame(self, bg=self._HEADER_BG)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        tk.Label(
            header,
            text="\U0001f916  RealAI v2.0",
            font=("Segoe UI", 18, "bold"),
            bg=self._HEADER_BG,
            fg=self._HEADER_FG,
            pady=12,
        ).pack()
        tk.Label(
            header,
            text="Enter your API keys below \u2014 they are saved locally, never uploaded",
            font=("Segoe UI", 9),
            bg=self._HEADER_BG,
            fg=self._HEADER_SUB,
            pady=2,
        ).pack()

        # Scrollable canvas + scrollbar for the API key form (row 1).
        self.rowconfigure(1, weight=1)
        _form_canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        _form_canvas.grid(row=1, column=0, sticky="nsew")
        _form_vscroll = tk.Scrollbar(self, orient="vertical", command=_form_canvas.yview)
        _form_vscroll.grid(row=1, column=1, sticky="ns")
        _form_canvas.configure(yscrollcommand=_form_vscroll.set)

        # Inner frame that holds all the provider rows.
        form = tk.Frame(_form_canvas, padx=pad, pady=pad)
        form.columnconfigure(0, weight=1)
        _form_win = _form_canvas.create_window((0, 0), window=form, anchor="nw")

        def _on_form_configure(event: tk.Event) -> None:
            _form_canvas.configure(scrollregion=_form_canvas.bbox("all"))

        def _on_canvas_resize(event: tk.Event) -> None:
            _form_canvas.itemconfig(_form_win, width=event.width)

        form.bind("<Configure>", _on_form_configure)
        _form_canvas.bind("<Configure>", _on_canvas_resize)

        # Mouse-wheel scrolling (Windows uses <MouseWheel>, Linux uses Button-4/5).
        def _on_mousewheel(event: tk.Event) -> None:
            if event.num == 4:
                _form_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                _form_canvas.yview_scroll(1, "units")
            else:
                _form_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        for widget in (form, _form_canvas):
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", _on_mousewheel)
            widget.bind("<Button-5>", _on_mousewheel)

        for row_idx, (provider_id, info) in enumerate(PROVIDERS.items()):
            base = row_idx * 3

            # Label
            lbl = tk.Label(
                form,
                text=f"{info['label']} API Key",
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            )
            lbl.grid(row=base, column=0, columnspan=2, sticky="w", pady=(pad // 2, 0))
            lbl.bind("<MouseWheel>", _on_mousewheel)
            lbl.bind("<Button-4>", _on_mousewheel)
            lbl.bind("<Button-5>", _on_mousewheel)

            # Password entry
            entry = tk.Entry(form, width=50, show="\u2022", font=("Consolas", 10))
            entry.grid(row=base + 1, column=0, sticky="ew", padx=(0, 6), pady=(2, 0))
            self._entries[provider_id] = entry

            # Eye toggle
            def _make_toggle(e: tk.Entry = entry) -> Callable[[], None]:
                def _toggle() -> None:
                    e.config(show="" if e.cget("show") else "\u2022")
                return _toggle

            tk.Button(
                form,
                text="\U0001f441",
                width=3,
                command=_make_toggle(),
                relief="flat",
                cursor="hand2",
            ).grid(row=base + 1, column=1, pady=(2, 0))

            # Help text
            help_lbl = tk.Label(
                form,
                text=info["help"],
                font=("Segoe UI", 8),
                fg="#777",
                anchor="w",
            )
            help_lbl.grid(row=base + 2, column=0, columnspan=2, sticky="w")
            help_lbl.bind("<MouseWheel>", _on_mousewheel)
            help_lbl.bind("<Button-4>", _on_mousewheel)
            help_lbl.bind("<Button-5>", _on_mousewheel)

        # Status bar — always visible below the scrollable form.
        self._status_var = tk.StringVar(value="Ready \u2014 enter your API keys above.")
        tk.Label(
            self,
            textvariable=self._status_var,
            font=("Segoe UI", 9),
            fg="#555",
            anchor="w",
            padx=pad,
            pady=4,
        ).grid(row=2, column=0, columnspan=2, sticky="ew")

        # Button row — always visible, never pushed off screen.
        btn_row = tk.Frame(self, padx=pad, pady=pad // 2)
        btn_row.grid(row=3, column=0, columnspan=2, sticky="ew")

        tk.Button(
            btn_row,
            text="\U0001f4be  Save Keys",
            width=14,
            font=("Segoe UI", 10),
            bg=self._BTN_SAVE,
            fg="white",
            activebackground="#1f5a39",
            relief="flat",
            cursor="hand2",
            command=self._save_keys,
        ).pack(side="left", padx=(0, 8))

        self._server_btn = tk.Button(
            btn_row,
            text="\U0001f680  Start API Server",
            width=18,
            font=("Segoe UI", 10),
            bg=self._BTN_START,
            fg="white",
            activebackground="#0d47a1",
            relief="flat",
            cursor="hand2",
            command=self._toggle_server,
        )
        self._server_btn.pack(side="left", padx=(0, 8))

        tk.Button(
            btn_row,
            text="\u2716  Clear All",
            width=10,
            font=("Segoe UI", 10),
            bg=self._BTN_STOP,
            fg="white",
            activebackground="#8b0000",
            relief="flat",
            cursor="hand2",
            command=self._clear_keys,
        ).pack(side="right")

        # Chat panel
        self._build_chat_panel()

    def _build_chat_panel(self) -> None:
        """Build the chat interface panel."""
        pad = self._PAD
        
        # Chat frame with border
        chat_frame = tk.LabelFrame(
            self,
            text="\U0001f4ac Chat with RealAI",
            font=("Segoe UI", 11, "bold"),
            padx=pad,
            pady=pad,
            relief="groove",
            borderwidth=2,
        )
        chat_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=pad, pady=(0, pad))
        self.rowconfigure(4, weight=1)
        
        # Conversation display (scrollable)
        self._chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            width=70,
            height=15,
            font=("Consolas", 10),
            state="disabled",
            bg="#f5f5f5",
            relief="sunken",
            borderwidth=2,
        )
        self._chat_display.pack(fill="both", expand=True, pady=(0, pad // 2))
        
        # Input row frame
        input_frame = tk.Frame(chat_frame)
        input_frame.pack(fill="x", pady=(pad // 2, 0))
        
        # Message input
        self._chat_input = tk.Entry(
            input_frame,
            font=("Segoe UI", 10),
            state="disabled",
        )
        self._chat_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._chat_input.bind("<Return>", lambda event: self._send_message())
        
        # Send button
        self._send_btn = tk.Button(
            input_frame,
            text="\u27a4  Send",
            width=10,
            font=("Segoe UI", 10),
            bg=self._BTN_START,
            fg="white",
            activebackground="#0d47a1",
            relief="flat",
            cursor="hand2",
            command=self._send_message,
            state="disabled",
        )
        self._send_btn.pack(side="left", padx=(0, 8))
        
        # Clear chat button
        tk.Button(
            input_frame,
            text="\u21ba  Clear Chat",
            width=12,
            font=("Segoe UI", 10),
            bg="#666",
            fg="white",
            activebackground="#444",
            relief="flat",
            cursor="hand2",
            command=self._clear_chat,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------

    def _load_saved_keys(self) -> None:
        """Populate entry fields from the saved config file."""
        config = load_config()
        for provider_id, entry in self._entries.items():
            value = config.get(provider_id, "")
            if value:
                entry.delete(0, tk.END)
                entry.insert(0, value)
        configured = [p for p in PROVIDERS if config.get(p)]
        if configured:
            names = ", ".join(PROVIDERS[p]["label"] for p in configured)
            self._status_var.set(f"Loaded saved keys for: {names}")

    def _save_keys(self) -> None:
        """Write the current entry values to disk and apply them as env vars."""
        config = {pid: entry.get().strip() for pid, entry in self._entries.items()}
        save_config(config)

        # Apply to the current process environment so a server subprocess inherits them.
        for provider_id, key in config.items():
            env_var = PROVIDERS[provider_id]["env_var"]
            if key:
                os.environ[env_var] = key
            else:
                os.environ.pop(env_var, None)

        configured = [p for p, v in config.items() if v]
        if configured:
            names = ", ".join(PROVIDERS[p]["label"] for p in configured)
            self._status_var.set(f"\u2705 Saved keys for: {names}")
        else:
            self._status_var.set("\u2705 Saved (no keys — RealAI runs in placeholder mode).")

    def _clear_keys(self) -> None:
        for entry in self._entries.values():
            entry.delete(0, tk.END)
        self._status_var.set("Keys cleared \u2014 click Save to persist.")

    # ------------------------------------------------------------------
    # Chat functionality
    # ------------------------------------------------------------------

    def _append_to_chat(self, text: str) -> None:
        """Append text to the chat display (safe to call from any thread)."""
        self._chat_display.config(state="normal")
        self._chat_display.insert(tk.END, text + "\n\n")
        self._chat_display.see(tk.END)
        self._chat_display.config(state="disabled")

    def _send_message(self) -> None:
        """Send a chat message to the local API server."""
        message = self._chat_input.get().strip()
        if not message:
            return
        
        # Clear input immediately
        self._chat_input.delete(0, tk.END)
        
        # Append user message to display
        self._append_to_chat(f"You: {message}")
        
        # Add to history
        self._chat_history.append({"role": "user", "content": message})
        
        # Disable input while processing
        self._chat_input.config(state="disabled")
        self._send_btn.config(state="disabled")
        
        # Send request in background thread
        threading.Thread(
            target=self._send_chat_request,
            args=(deepcopy(self._chat_history),),
            daemon=True,
        ).start()

    def _send_chat_request(self, history: List[Dict[str, str]]) -> None:
        """Background thread: POST to the API server and update UI."""
        try:
            # Prepare request
            url = f"{self._API_BASE_URL}/v1/chat/completions"
            data = json.dumps({
                "messages": history,
                "model": self._DEFAULT_MODEL
            }, ensure_ascii=False).encode("utf-8")
            
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            
            # Send request
            with urllib.request.urlopen(req, timeout=self._API_TIMEOUT) as response:
                response_data = json.loads(response.read().decode("utf-8"))
            
            # Extract AI response with validation
            if "choices" not in response_data or not response_data["choices"]:
                raise KeyError("Response missing 'choices' field or empty choices array")
            
            choice = response_data["choices"][0]
            if "message" not in choice or "content" not in choice["message"]:
                raise KeyError("Response missing 'message' or 'content' field")
            
            ai_message = choice["message"]["content"]
            
            # Update history and display in main thread
            self.after(0, self._on_chat_response, ai_message)
            
        except urllib.error.URLError as exc:
            # Extract user-friendly error message
            error_detail = str(exc)
            if hasattr(exc, 'reason'):
                error_detail = str(exc.reason)
            error_msg = f"Cannot connect to API server: {error_detail}"
            self.after(0, self._on_chat_error, error_msg)
        except (KeyError, json.JSONDecodeError, IndexError) as exc:
            error_msg = f"Invalid response format: {exc}"
            self.after(0, self._on_chat_error, error_msg)
        except Exception as exc:
            error_msg = f"Unexpected error: {exc}"
            self.after(0, self._on_chat_error, error_msg)

    def _on_chat_response(self, ai_message: str) -> None:
        """Handle successful AI response (main thread)."""
        self._chat_history.append({"role": "assistant", "content": ai_message})
        self._append_to_chat(f"AI: {ai_message}")
        
        # Re-enable input
        if self._server_proc and self._server_proc.poll() is None:
            self._chat_input.config(state="normal")
            self._send_btn.config(state="normal")

    def _on_chat_error(self, error_msg: str) -> None:
        """Handle chat error (main thread)."""
        self._append_to_chat(f"AI: [Error: {error_msg}]")
        
        # Re-enable input
        if self._server_proc and self._server_proc.poll() is None:
            self._chat_input.config(state="normal")
            self._send_btn.config(state="normal")

    def _clear_chat(self) -> None:
        """Clear the chat history and display."""
        self._chat_history.clear()
        self._chat_display.config(state="normal")
        self._chat_display.delete("1.0", tk.END)
        self._chat_display.config(state="disabled")

    # ------------------------------------------------------------------
    # Server control
    # ------------------------------------------------------------------

    def _toggle_server(self) -> None:
        if self._server_proc and self._server_proc.poll() is None:
            self._stop_server()
        else:
            self._start_server()

    def _start_server(self) -> None:
        """Save keys, then launch api_server.py in a subprocess."""
        self._save_keys()
        server_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "api_server.py"
        )
        # Build child env inheriting the updated os.environ (which now has API keys).
        try:
            self._server_proc = subprocess.Popen(
                [sys.executable, server_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as exc:
            messagebox.showerror("Server Error", f"Could not start server:\n{exc}")
            return

        self._server_btn.config(
            text="\u23f9  Stop API Server",
            bg=self._BTN_STOP,
            activebackground="#8b0000",
        )
        self._status_var.set("\U0001f680 API server started \u2014 http://localhost:8000")
        
        # Enable chat UI
        self._chat_input.config(state="normal")
        self._send_btn.config(state="normal")
        
        threading.Thread(target=self._monitor_server, daemon=True).start()

    def _stop_server(self) -> None:
        if self._server_proc:
            self._server_proc.terminate()
            self._server_proc = None
        self._server_btn.config(
            text="\U0001f680  Start API Server",
            bg=self._BTN_START,
            activebackground="#0d47a1",
        )
        self._status_var.set("\u23f9 API server stopped.")
        
        # Disable chat UI
        self._chat_input.config(state="disabled")
        self._send_btn.config(state="disabled")

    def _monitor_server(self) -> None:
        """Background thread: update the button when the server exits on its own."""
        if self._server_proc:
            self._server_proc.wait()
            self.after(0, self._on_server_exit)

    def _on_server_exit(self) -> None:
        self._server_proc = None
        self._server_btn.config(
            text="\U0001f680  Start API Server",
            bg=self._BTN_START,
            activebackground="#0d47a1",
        )
        self._status_var.set("\u26a0\ufe0f API server exited unexpectedly.")
        
        # Disable chat UI
        self._chat_input.config(state="disabled")
        self._send_btn.config(state="disabled")

    # ------------------------------------------------------------------
    # Window lifecycle
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        if self._server_proc and self._server_proc.poll() is None:
            self._stop_server()
        self.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = RealAILauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
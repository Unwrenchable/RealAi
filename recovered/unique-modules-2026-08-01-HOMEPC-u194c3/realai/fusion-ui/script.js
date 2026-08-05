/* ==================== RealAI Fusion UI Config ==================== */
// Single BACKEND_BASE — no duplicates.
// Prefer same-origin when UI is served by the API server itself.
// Fallback to localhost:8000 for standalone/static hosting.
const CONFIG = (() => {
  // Deterministic backend base resolution:
  // 1) If served from the API server (port 8000), use same-origin.
  // 2) If served from any other port, force port to 8000.
  // 3) If we can't compute origin, fallback to http://127.0.0.1:8000.
  let base = 'http://127.0.0.1:8000';

  if (typeof window !== 'undefined' && window.location) {
    try {
      const originUrl = new URL(window.location.origin);
      // Always force backend port to 8000.
      originUrl.port = '8000';
      base = originUrl.origin;
    } catch (_) {
      // keep fallback
    }
  }

  window.__REALAI_BACKEND_BASE__ = base;

  return {
    BACKEND_BASE: base,
    API_KEY: (typeof REALAI_API_KEY !== 'undefined' && REALAI_API_KEY) ? REALAI_API_KEY : '',
  };
})();

const BACKEND_BASE = CONFIG.BACKEND_BASE;
const API_KEY = CONFIG.API_KEY;

console.log('🔧 [FusionUI] Using RealAI BACKEND_BASE =', BACKEND_BASE);

async function apiCall(endpoint, options = {}) {
  const url = `${BACKEND_BASE}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  console.log('🔗 Calling:', url);

  const fetchOptions = {
    ...options,
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json',
      ...(API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {}),
      ...(options.headers || {}),
    },
  };

  const response = await fetch(url, fetchOptions);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} - ${response.statusText}`);
  }
  return response;
}

// Health check on load
async function checkBackend() {
  const healthUrl = `${BACKEND_BASE}/health`;
  try {
    const res = await apiCall('/health');
    const data = await res.json();
    console.log('✅ Backend OK:', data);
    window.__REALAI_MODEL__ = data?.model || window.__REALAI_MODEL__;
  } catch (err) {
    console.error('❌ Backend unreachable:', err);

    // Visible error banner for Fusion UI
    let banner = document.getElementById('backend-error-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'backend-error-banner';
      banner.style.cssText =
        'margin:8px 0;padding:8px 12px;border:1px solid rgba(255,80,80,0.6);' +
        'border-radius:6px;background:rgba(40,0,0,0.55);color:#ffb3b3;' +
        'font-family:Consolas,monospace;font-size:12px;';
      const panelChat = document.getElementById('panel-chat');
      if (panelChat && panelChat.parentNode) {
        panelChat.parentNode.insertBefore(banner, panelChat);
      } else {
        document.body.prepend(banner);
      }
    }

    const msg =
      `Cannot reach RealAI backend. Tried: ${healthUrl}. ` +
      `Start the server (realai_server.py) and ensure PORT=8000 is bound.`;
    banner.textContent = msg;

    if (typeof showError === 'function') {
      showError(msg);
    }
  }
}


window.addEventListener('load', checkBackend);

const chatLog = document.getElementById('chat-log');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');

const overseerLog = document.getElementById('overseer-log');
const consoleLog = document.getElementById('console-log');
const consoleForm = document.getElementById('console-form');
const consoleInput = document.getElementById('console-input');

const requestViewer = document.getElementById('request-viewer');

const gpuSpan = document.getElementById('gpu-load');
const cpuSpan = document.getElementById('cpu-load');
const vramSpan = document.getElementById('vram-usage');
const threadSpan = document.getElementById('thread-count');

/* Theme switching */
document.querySelectorAll('.mode-switcher button').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.body.className = btn.dataset.theme;
  });
});

/* Fake system metrics (wire to real stats later) */
function updateFakeMetrics() {
  const gpu = (10 + Math.random() * 40).toFixed(0) + '%';
  const cpu = (5 + Math.random() * 60).toFixed(0) + '%';
  const vram = (1.5 + Math.random() * 4).toFixed(1) + ' GB';
  const threads = (2 + Math.random() * 10).toFixed(0);

  gpuSpan.textContent = gpu;
  cpuSpan.textContent = cpu;
  vramSpan.textContent = vram;
  threadSpan.textContent = threads;

  const gpuNum = parseInt(gpu, 10);
  const cpuNum = parseInt(cpu, 10);
  autoModeSwitch(gpuNum, cpuNum);
}
setInterval(updateFakeMetrics, 4000);

function logOverseer(text) {
  const div = document.createElement('div');
  div.textContent = text;
  overseerLog.appendChild(div);
  overseerLog.scrollTop = overseerLog.scrollHeight;
}

function logConsole(text) {
  const div = document.createElement('div');
  div.textContent = text;
  consoleLog.appendChild(div);
  consoleLog.scrollTop = consoleLog.scrollHeight;
}

function appendChatMessage(role, text) {
  const div = document.createElement('div');
  div.className = `chat-message ${role}`;
  div.textContent = (role === 'user' ? 'You: ' : 'Overseer: ') + text;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

/* Auto theme switching based on load */
function autoModeSwitch(gpuLoad, cpuLoad) {
  if (gpuLoad > 60 || cpuLoad > 70) {
    document.body.className = 'theme-neon';
    logOverseer('High load detected. Engaging Neon Reactor mode.');
  } else if (gpuLoad < 25 && cpuLoad < 30) {
    document.body.className = 'theme-pipboy';
    logOverseer('System idle. Pip‑Boy Retro mode active.');
  } else {
    document.body.className = 'theme-fusion';
    logOverseer('Balanced load. Fusion mode engaged.');
  }
}

async function sendMessageToBackend(userText) {
  try {
    const payload = {
      model: window.__REALAI_MODEL__ || 'realai-2.0',
      messages: [
        {
          role: 'user',
          content: userText,
        },
      ],
    };

    requestViewer.textContent = JSON.stringify(payload, null, 2);
    logConsole('Sending request to RealAI…');

    const response = await apiCall('/v1/chat/completions', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    const content =
      data.choices?.[0]?.message?.content ||
      data.content ||
      'No response received.';

    // UI compatibility: only appendChatMessage if no other renderer exists
    if (typeof renderMessage === 'function') {
      renderMessage('assistant', content);
    }
    appendChatMessage('assistant', content);
    logOverseer('Overseer responded to latest prompt.');
  } catch (error) {
    console.error('Chat failed:', error);
    logConsole('Error: ' + (error?.message || String(error)));
    appendChatMessage('ai', '[Error contacting RealAI backend]');

    if (typeof showError === 'function') {
      showError('Failed to contact RealAI backend. Is it running on 8000?');
    }
  }
}

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  chatInput.value = '';
  appendChatMessage('user', text);
  await sendMessageToBackend(text);
});

consoleForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const cmd = consoleInput.value.trim();
  if (!cmd) return;

  consoleInput.value = '';
  logConsole('> ' + cmd);

  if (cmd === '/reload') {
    logConsole('Reloading UI (simulated).');
    logOverseer('UI reload requested.');
  } else if (cmd.startsWith('/switch')) {
    logConsole('Model switch requested: ' + cmd);
    logOverseer('Model switch command received.');
  } else if (cmd === '/inspect') {
    logConsole('Inspector mode (simulated).');
    logOverseer('Inspector mode toggled.');
  } else {
    logConsole('Unknown command.');
  }
});

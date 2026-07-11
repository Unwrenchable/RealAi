/* ==================== RealAI Fusion UI Config ==================== */
const CONFIG = (() => {
  let base = 'http://127.0.0.1:8000';

  if (typeof window !== 'undefined' && window.location) {
    try {
      const originUrl = new URL(window.location.origin);
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

function byId(id) {
  return document.getElementById(id);
}

function ensureContainer(id, tag = 'div') {
  let el = byId(id);
  if (!el) {
    el = document.createElement(tag);
    el.id = id;
    document.body.appendChild(el);
  }
  return el;
}

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
    let details = '';
    try {
      const errJson = await response.json();
      details = errJson?.error?.message || '';
    } catch (_) {
      // ignore parse failure
    }
    const suffix = details ? `: ${details}` : '';
    throw new Error(`HTTP ${response.status} - ${response.statusText}${suffix}`);
  }
  return response;
}

function showBanner(msg, isError = false) {
  let banner = byId('backend-error-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'backend-error-banner';
    banner.style.cssText =
      'margin:8px 0;padding:8px 12px;border:1px solid rgba(120,120,255,0.4);' +
      'border-radius:6px;background:rgba(10,10,30,0.7);color:#dce2ff;' +
      'font-family:Consolas,monospace;font-size:12px;';
    document.body.prepend(banner);
  }
  if (isError) {
    banner.style.borderColor = 'rgba(255,80,80,0.6)';
    banner.style.background = 'rgba(40,0,0,0.55)';
    banner.style.color = '#ffb3b3';
  } else {
    banner.style.borderColor = 'rgba(120,120,255,0.4)';
    banner.style.background = 'rgba(10,10,30,0.7)';
    banner.style.color = '#dce2ff';
  }
  banner.textContent = msg;
}

function setHealthIndicator(ok, text) {
  const indicator = byId('health-indicator');
  if (!indicator) return;
  indicator.textContent = text;
  indicator.style.color = ok ? '#8cffb0' : '#ffb3b3';
}

async function checkBackend() {
  const healthUrl = `${BACKEND_BASE}/health`;
  try {
    const res = await apiCall('/health');
    const data = await res.json();
    console.log('✅ Backend OK:', data);
    window.__REALAI_MODEL__ = data?.model || window.__REALAI_MODEL__ || 'realai-2.0';
    showBanner(`Backend connected: ${healthUrl}`);
    setHealthIndicator(true, 'Health: connected');
  } catch (err) {
    console.error('❌ Backend unreachable:', err);
    showBanner(
      `Cannot reach RealAI backend. Tried: ${healthUrl}. Start realai_server.py on port 8000.`,
      true
    );
    setHealthIndicator(false, 'Health: unreachable');
  }
}

function appendChatMessage(role, text) {
  const chatLog = ensureContainer('chat-log');
  const div = document.createElement('div');
  div.className = `chat-message ${role}`;
  div.textContent = (role === 'user' ? 'You: ' : 'Overseer: ') + text;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function sendMessageToBackend(userText) {
  const requestViewer = byId('request-viewer');
  try {
    const payload = {
      model: window.__REALAI_MODEL__ || 'realai-2.0',
      messages: [{ role: 'user', content: userText }],
    };

    if (requestViewer) {
      requestViewer.textContent = JSON.stringify(payload, null, 2);
    }

    const response = await apiCall('/v1/chat/completions', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    const content =
      data?.choices?.[0]?.message?.content ||
      data?.content ||
      'No response received.';

    appendChatMessage('assistant', content);
  } catch (error) {
    console.error('Chat failed:', error);
    appendChatMessage('assistant', '[Error contacting RealAI backend]');
    const msg = String(error?.message || '');
    if (msg.includes('HTTP 400')) {
      showBanner(`Request rejected (400): ${msg}`, true);
    } else {
      showBanner('Failed to contact RealAI backend. Is it running on 8000?', true);
    }
  }
}

function mountMinimalChatIfMissing() {
  let chatForm = byId('chat-form');
  let chatInput = byId('chat-input');

  if (!chatForm || !chatInput) {
    const wrapper = document.createElement('div');
    wrapper.style.marginTop = '16px';
    wrapper.innerHTML = `
      <div id="chat-log" style="padding:8px;border:1px solid #2f2f5f;border-radius:8px;min-height:120px;margin-bottom:8px;"></div>
      <form id="chat-form" style="display:flex;gap:8px;">
        <input id="chat-input" type="text" placeholder="Type a message..." style="flex:1;padding:8px;border-radius:6px;border:1px solid #555;" />
        <button type="submit" style="padding:8px 12px;">Send</button>
      </form>
    `;
    document.body.appendChild(wrapper);
    chatForm = byId('chat-form');
    chatInput = byId('chat-input');
  }

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = (chatInput.value || '').trim();
    if (!text) return;
    chatInput.value = '';
    appendChatMessage('user', text);
    await sendMessageToBackend(text);
  });
}

window.addEventListener('load', async () => {
  await checkBackend();
  mountMinimalChatIfMissing();
});

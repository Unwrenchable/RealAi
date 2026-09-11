"""Rebrand AgentX dashboard HTML into RealAI agents-ui/index.html."""
from __future__ import annotations

from pathlib import Path

SRC = Path(r"C:\RealAI-clean\agents-ui\_from_agentx.html")
OUT = Path(r"C:\RealAI-clean\agents-ui\index.html")

RUN_DOCK = r"""
<div id="run-dock" style="position:fixed;left:50%;transform:translateX(-50%);bottom:14px;z-index:150;background:#141428;border:1px solid #2f2f5f;border-radius:12px;padding:10px 12px;display:flex;gap:8px;align-items:center;box-shadow:0 8px 30px rgba(0,0,0,.45);max-width:920px;width:calc(100% - 28px)">
  <select id="run-agent" style="background:#0b0b16;color:#e4e4ff;border:1px solid #2f2f5f;border-radius:8px;padding:8px;min-width:160px"></select>
  <input id="run-task" placeholder="Task for agent / hive multi-agent…" style="flex:1;background:#0b0b16;color:#e4e4ff;border:1px solid #2f2f5f;border-radius:8px;padding:8px" />
  <label style="font-size:11px;color:#9fa7d9;white-space:nowrap"><input type="checkbox" id="run-multi" checked /> multi</label>
  <button id="run-btn" style="background:#7c5cfc;color:#fff;border:none;border-radius:8px;padding:8px 14px;cursor:pointer;font-weight:600">Run</button>
  <button id="sim-btn" style="background:transparent;color:#9fa7d9;border:1px solid #2f2f5f;border-radius:8px;padding:8px 10px;cursor:pointer">Sim</button>
  <a href="/fusion-ui/" style="color:#a78bfa;font-size:12px;text-decoration:none">Fusion</a>
  <a href="/console" style="color:#a78bfa;font-size:12px;text-decoration:none">Console</a>
</div>
<script>
(function(){
  function fillAgents(){
    const sel=document.getElementById('run-agent');
    if(!sel||!st.agents) return;
    sel.innerHTML = st.agents.slice().sort((a,b)=>a.id.localeCompare(b.id)).map(a=>`<option value="${a.id}">${a.id}</option>`).join('');
    const prefer=['ai-orchestrator','hive-orchestrator','hive-mind-coordinator','coder','architect'];
    for(const p of prefer){ const o=[...sel.options].find(x=>x.value===p); if(o){ sel.value=p; break; } }
  }
  const _init=init;
  init=async function(){ await _init(); fillAgents(); };
  document.getElementById('run-btn').onclick=async()=>{
    const agent_id=document.getElementById('run-agent').value;
    const task=document.getElementById('run-task').value.trim();
    if(!task) return;
    const multi=document.getElementById('run-multi').checked;
    document.getElementById('run-btn').disabled=true;
    try{
      const r=await fetch(API+'/v1/agents/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agent_id,task,multi})});
      const j=await r.json();
      console.log('run', j);
    }catch(e){ console.error(e); }
    document.getElementById('run-btn').disabled=false;
  };
  document.getElementById('sim-btn').onclick=async()=>{
    try{
      const r=await fetch(API+'/v1/agents/simulation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({toggle:true})});
      const j=await r.json();
      document.getElementById('sim-btn').textContent = j.enabled ? 'Sim ON' : 'Sim OFF';
    }catch(e){}
  };
})();
</script>
"""

INJECT_API = """
const API = (typeof window !== 'undefined' && window.location && (window.location.pathname === '/agents-ui' || window.location.pathname.indexOf('/agents-ui/') === 0))
  ? window.location.origin : (window.__REALAI_BACKEND_BASE__ || 'http://127.0.0.1:8001');
"""

AGENTS_PARSE = """const _ar=await ar.json();
  st.agents=Array.isArray(_ar)?_ar:(_ar.data||_ar.nodes||[]);
  st.agents=st.agents.map(a=>({
    id:a.id, role:a.role||a.id, description:a.description||'',
    tags:a.tags||[], capabilities:a.capabilities||[],
    required_tools:a.required_tools||[],
    preferred_profile:a.preferred_profile||'balanced',
    risk_level:a.risk_level||'medium'
  }));"""


def main() -> None:
    html = SRC.read_text(encoding="utf-8")
    repls = [
        ("AgentX — Workflow Dashboard | AI Agent Registry & Orchestration", "RealAI — Agent Activity"),
        ("AgentX — AI Agent Workflow Dashboard", "RealAI — Agent Activity"),
        ("AgentX Dashboard", "RealAI Agent Activity"),
        ("AgentX live workflow dashboard", "RealAI live agent activity"),
        ("#0d1117", "#0b0b16"),
        ("#161b22", "#141428"),
        ("#30363d", "#2f2f5f"),
        ("#58a6ff", "#7c5cfc"),
        ("#e6edf3", "#e4e4ff"),
        ("#8b949e", "#9fa7d9"),
        ("#21262d", "#1a1a32"),
        ("#1c2128", "#181830"),
        ("#79c0ff", "#a78bfa"),
        ("fetch('/api/agents')", "fetch(API+'/v1/agents?full=1')"),
        ("fetch('/api/profiles')", "fetch(API+'/v1/agents/profiles')"),
        ("fetch('/api/graph')", "fetch(API+'/v1/agents/graph')"),
        ("new EventSource('/api/events')", "new EventSource(API+'/v1/agents/events')"),
        ("&#11041;", "◈"),
    ]
    for a, b in repls:
        html = html.replace(a, b)

    html = html.replace("const RISK_COLOR", INJECT_API + "\nconst RISK_COLOR")
    html = html.replace("st.agents=await ar.json();", AGENTS_PARSE)
    # profiles may be list already
    html = html.replace(
        "st.profiles=await pr.json();",
        "const _pr=await pr.json(); st.profiles=Array.isArray(_pr)?_pr:(_pr.data||[]);",
    )
    html = html.replace("</body>", RUN_DOCK + "\n</body>")
    # leave room for dock
    html = html.replace("#act-feed{flex:1;", "#act-feed{flex:1;padding-bottom:72px;")
    html = html.replace(
        "body{background:#0b0b16;color:#e4e4ff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;height:100vh;overflow:hidden}",
        "body{background:#0b0b16;color:#e4e4ff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;height:100vh;overflow:hidden}",
    )
    OUT.write_text(html, encoding="utf-8")
    print("wrote", OUT, "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()

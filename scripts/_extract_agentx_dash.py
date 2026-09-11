from pathlib import Path

src = Path(r"C:\Users\tsmit\agent_tools_\agent_tools\dashboard.py").read_text(encoding="utf-8")
marker = '_HTML = """'
start = src.index(marker) + len(marker)
end = src.index('"""', start)
html = src[start:end]
out_dir = Path(r"C:\RealAI-clean\agents-ui")
out_dir.mkdir(exist_ok=True)
(out_dir / "_from_agentx.html").write_text(html, encoding="utf-8")
print("bytes", len(html))

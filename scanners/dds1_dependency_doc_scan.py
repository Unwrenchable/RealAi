import os, json, re, hashlib

ROOT = "C:\\realai"
OUT = "C:\\realai\\scan_results\\dds1_dependency_doc_manifest.json"

# -----------------------------
# FILE TYPES TO SCAN
# -----------------------------
DOC_EXT = [
    ".md",".txt",".rst",".json",".yaml",".yml",".toml",".cfg",".ini",
    "requirements.txt","environment.yml","package.json","pyproject.toml"
]

# -----------------------------
# KEYWORDS TO CATCH MISSING FEATURES
# -----------------------------
DOC_KEYWORDS = [

    # Docs referencing subsystems
    "agent","agents","memory","worldmodel","simulation","npc","quest",
    "plugin","mcp","connector","extension","workflow","lora","training",
    "gpu","cuda","rocm","vllm","ollama","rag","retrieval","faiss",
    "chromadb","pinecone","qdrant","weaviate","solana","anchor","program",
    "postgres","redis","docker","kubernetes","helm","vercel","render",

    # Docs referencing RealAI features
    "realai","realai_server","realai_plugin","realai_mcp","realai_worldmodel",
    "realai_lora","realai_solana","realai_hivemind","hive_mind",

    # TODO / FIXME / missing work
    "todo","fixme","unfinished","deprecated","rewrite","upgrade","missing",
    "planned","future","prototype","experimental"
]

# -----------------------------
# DEPENDENCY PATTERNS
# -----------------------------
DEPENDENCY_PATTERNS = [
    r"[a-zA-Z0-9_\-]+==[0-9\.]+",      # Python pinned deps
    r"[a-zA-Z0-9_\-]+>=?[0-9\.]+",    # Python versioned deps
    r"\"[a-zA-Z0-9_\-]+\":\s*\"[0-9\.]+\"",  # Node deps
    r"[a-zA-Z0-9_\-]+",               # generic dependency names
]

# -----------------------------
# HASHING
# -----------------------------
def hash_file(path):
    try:
        with open(path,"rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return None

# -----------------------------
# SCAN FILE
# -----------------------------
def scan_file(path):
    hits = []
    try:
        with open(path,"r",encoding="utf-8",errors="ignore") as f:
            lines = f.readlines()
    except:
        return hits

    # Keyword hits
    for i,line in enumerate(lines):
        for kw in DOC_KEYWORDS:
            if kw.lower() in line.lower():
                hits.append({
                    "type":"keyword",
                    "keyword":kw,
                    "line":i+1,
                    "context":"".join(lines[max(0,i-10):min(len(lines),i+10)])
                })

    # Dependency hits
    for i,line in enumerate(lines):
        for pattern in DEPENDENCY_PATTERNS:
            if re.search(pattern,line):
                hits.append({
                    "type":"dependency",
                    "pattern":pattern,
                    "line":i+1,
                    "context":line.strip()
                })

    return hits

# -----------------------------
# WALK DIRECTORY
# -----------------------------
def walk(root):
    manifest = []
    for dp,_,files in os.walk(root):
        for f in files:
            if any(f.lower().endswith(ext) for ext in DOC_EXT) or f.lower() in DOC_EXT:
                full = os.path.join(dp,f)
                results = scan_file(full)
                if results:
                    manifest.append({
                        "file":full,
                        "hash":hash_file(full),
                        "hits":results
                    })
    return manifest

# -----------------------------
# MAIN
# -----------------------------
if __name__=="__main__":
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    manifest = walk(ROOT)
    with open(OUT,"w",encoding="utf-8") as f:
        json.dump(manifest,f,indent=2)
    print(f"[DDS‑1] Dependency & Documentation Scan Complete → {OUT}")

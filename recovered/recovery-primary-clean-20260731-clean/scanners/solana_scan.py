import os, json, hashlib

ROOT="C:\\realai"
OUT="C:\\realai\\scan_results\\solana_manifest.json"

KEYWORDS=[
    "solana","textsolana","solders","anchor","program_id","pda",
    "bonding_curve","token_mint","zk_compression","c_nft","cnft"
]

EXTENSIONS=[".py",".js",".ts",".json",".md",".txt",".yaml",".yml"]

def hash_file(p):
    try:
        with open(p,"rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return None

def scan_file(path):
    hits=[]
    try:
        with open(path,"r",encoding="utf-8",errors="ignore") as f:
            lines=f.readlines()
    except:
        return hits

    for i,line in enumerate(lines):
        for kw in KEYWORDS:
            if kw.lower() in line.lower():
                hits.append({
                    "keyword":kw,
                    "line":i+1,
                    "context":"".join(lines[max(0,i-10):min(len(lines),i+10)])
                })
    return hits

def walk(root):
    manifest=[]
    for dp,_,files in os.walk(root):
        for f in files:
            if any(f.lower().endswith(ext) for ext in EXTENSIONS):
                full=os.path.join(dp,f)
                results=scan_file(full)
                if results:
                    manifest.append({
                        "file":full,
                        "hash":hash_file(full),
                        "hits":results
                    })
    return manifest

if __name__=="__main__":
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    manifest=walk(ROOT)
    with open(OUT,"w",encoding="utf-8") as f:
        json.dump(manifest,f,indent=2)
    print(f"[SOLANA‑SCAN] Solana Scan Complete → {OUT}")

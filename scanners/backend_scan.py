import os, json, hashlib

ROOT="C:\\realai"
OUT="C:\\realai\\scan_results\\backend_manifest.json"

KEYWORDS=[
    "docker","dockerfile","compose","kubernetes","helm","fastify",
    "express","nextjs","vercel","render.com","postgres","postgis",
    "pgvector","redis","celery"
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


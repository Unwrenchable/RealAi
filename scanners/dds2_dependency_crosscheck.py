import os, json, re, hashlib

ROOT = "C:\\realai"
OUT = "C:\\realai\\scan_results\\dds2_dependency_crosscheck.json"

# -----------------------------
# FILES TO PARSE FOR DEPENDENCIES
# -----------------------------
DEPENDENCY_FILES = [
    "requirements.txt",
    "environment.yml",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "pyrightconfig.json"
]

# -----------------------------
# REGEX PATTERNS
# -----------------------------
PY_IMPORT = r"^\s*(import|from)\s+([a-zA-Z0-9_\.]+)"
NODE_REQUIRE = r"require\(['\"]([a-zA-Z0-9_\-\/]+)['\"]\)"
NODE_IMPORT = r"import\s+.*?from\s+['\"]([a-zA-Z0-9_\-\/]+)['\"]"

PY_DEP = r"([a-zA-Z0-9_\-]+)==?[0-9\.]*"
NODE_DEP = r"\"([a-zA-Z0-9_\-]+)\":\s*\"?[0-9\.]+\"?"

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
# READ DEPENDENCY FILES
# -----------------------------
def read_dependency_files(root):
    deps = {
        "python_declared": set(),
        "node_declared": set(),
        "config_declared": set()
    }

    for dp,_,files in os.walk(root):
        for f in files:
            if f.lower() in DEPENDENCY_FILES:
                full = os.path.join(dp,f)
                try:
                    with open(full,"r",encoding="utf-8",errors="ignore") as fh:
                        text = fh.read()
                except:
                    continue

                # Python deps
                for m in re.findall(PY_DEP, text):
                    deps["python_declared"].add(m.lower())

                # Node deps
                for m in re.findall(NODE_DEP, text):
                    deps["node_declared"].add(m.lower())

                # Generic config deps
                for m in re.findall(r"[a-zA-Z0-9_\-]+", text):
                    deps["config_declared"].add(m.lower())

    return deps

# -----------------------------
# SCAN CODE FOR IMPORTS
# -----------------------------
def scan_code_imports(root):
    imports = {
        "python_imports": set(),
        "node_imports": set()
    }

    for dp,_,files in os.walk(root):
        for f in files:
            if f.lower().endswith((".py",".js",".ts")):
                full = os.path.join(dp,f)
                try:
                    with open(full,"r",encoding="utf-8",errors="ignore") as fh:
                        lines = fh.readlines()
                except:
                    continue

                for line in lines:
                    # Python imports
                    m = re.search(PY_IMPORT, line)
                    if m:
                        imports["python_imports"].add(m.group(2).split(".")[0].lower())

                    # Node require()
                    m = re.search(NODE_REQUIRE, line)
                    if m:
                        imports["node_imports"].add(m.group(1).lower())

                    # Node import from
                    m = re.search(NODE_IMPORT, line)
                    if m:
                        imports["node_imports"].add(m.group(1).lower())

    return imports

# -----------------------------
# CROSS CHECK
# -----------------------------
def cross_check(declared, imported):
    results = {
        "missing_python_dependencies": [],
        "unused_python_dependencies": [],
        "missing_node_dependencies": [],
        "unused_node_dependencies": [],
        "declared_not_imported": [],
        "imported_not_declared": []
    }

    # Python
    for dep in imported["python_imports"]:
        if dep not in declared["python_declared"]:
            results["missing_python_dependencies"].append(dep)

    for dep in declared["python_declared"]:
        if dep not in imported["python_imports"]:
            results["unused_python_dependencies"].append(dep)

    # Node
    for dep in imported["node_imports"]:
        if dep not in declared["node_declared"]:
            results["missing_node_dependencies"].append(dep)

    for dep in declared["node_declared"]:
        if dep not in imported["node_imports"]:
            results["unused_node_dependencies"].append(dep)

    # Declared but not imported (generic)
    for dep in declared["config_declared"]:
        if dep not in imported["python_imports"] and dep not in imported["node_imports"]:
            results["declared_not_imported"].append(dep)

    # Imported but not declared
    for dep in imported["python_imports"]:
        if dep not in declared["python_declared"]:
            results["imported_not_declared"].append(dep)

    for dep in imported["node_imports"]:
        if dep not in declared["node_declared"]:
            results["imported_not_declared"].append(dep)

    return results

# -----------------------------
# MAIN
# -----------------------------
if __name__=="__main__":
    os.makedirs(os.path.dirname(OUT),exist_ok=True)

    declared = read_dependency_files(ROOT)
    imported = scan_code_imports(ROOT)
    results = cross_check(declared, imported)

    with open(OUT,"w",encoding="utf-8") as f:
        json.dump({
            "declared_dependencies": declared,
            "imported_dependencies": imported,
            "crosscheck_results": results
        }, f, indent=2)

    print(f"[DDS‑2] Dependency Cross‑Check Complete → {OUT}")

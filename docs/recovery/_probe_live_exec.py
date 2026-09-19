from realai.bot.live_exec import try_live_exec, wants_live_exec

cases = [
    "$ whoami",
    "/run dir",
    "run `hostname`",
    "run whoami",
    "run dir",
    "I type and run commands. Prefer tools. Never invent stdout.",
    (
        "Work like a desktop coding agent (same loop as our Grok Bot sessions), "
        "not a chatbot.\nLOOP - every request:\n1) INSPECT - read/list/grep\n"
        "Prove it: read docs/CONSOLE_OPERATOR_DIRECTIVE.md"
    ),
    "read docs/CONSOLE_OPERATOR_DIRECTIVE.md",
    "create file docs/x.txt with content HI",
    "/run",
]
for t in cases:
    w = wants_live_exec(t)
    d = try_live_exec(t)
    surf = None if d is None else d.get("surface")
    err = None if d is None else (d.get("result") or {}).get("error")
    print(repr(t[:72]), "wants", w, "surf", surf, "err", err)

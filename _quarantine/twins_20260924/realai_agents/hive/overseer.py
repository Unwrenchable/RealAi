from agents.hive import run_agent


def run(task: str = "", **kwargs):
    return run_agent("overseer", task, **kwargs)


if __name__ == "__main__":
    print(run("Initialize hive orchestration"))

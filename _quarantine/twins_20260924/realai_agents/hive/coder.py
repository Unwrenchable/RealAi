from agents.hive import run_agent


def run(task: str = "", **kwargs):
    return run_agent("coder", task, **kwargs)


if __name__ == "__main__":
    print(run("Implement a small safe fix"))

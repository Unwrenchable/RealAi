from agents.hive import run_agent


def run(task: str = "", **kwargs):
    return run_agent("governor", task, **kwargs)


if __name__ == "__main__":
    print(run("Validate safe execution constraints"))

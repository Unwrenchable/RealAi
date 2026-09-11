from agents.hive import run_agent


def run(task: str = "", **kwargs):
    return run_agent("router", task, **kwargs)


if __name__ == "__main__":
    print(run("Route models for hive agents"))

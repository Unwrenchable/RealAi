"""Offline tests: device_profile recommendations (mocked hardware) and chess source formatting."""
import pytest

from realai.core import device_profile as D


def _p(gpus, vk=None, dml=None, ram=32, hints=None):
    return {"os": "Windows 11", "ram_gb": ram, "cpu_threads": 16, "gpus": gpus, "vulkan_devices": vk or [],
            "directml_adapters": dml or [], "hints": hints or {}}


def test_parse_llama_list_devices():
    txt = "Available devices:\n  Vulkan0: AMD Radeon(TM) Graphics (8192 MiB, 8000 MiB free)\n  Vulkan1: AMD Radeon RX 6700 XT (12272 MiB, 11883 MiB free)\n"
    d = D.parse_llama_list_devices(txt)
    assert [x["id"] for x in d] == ["Vulkan0", "Vulkan1"] and d[1]["vram_gb"] == round(12272 / 1024, 2)


def test_picks_discrete_even_when_igpu_enumerates_first():
    vk = D.parse_llama_list_devices("Vulkan0: AMD Radeon(TM) Graphics (8192 MiB)\nVulkan1: AMD Radeon RX 6700 XT (12272 MiB)")
    r = D.recommend(_p([{"name": "AMD Radeon(TM) Graphics", "vram_gb": 0.5}, {"name": "AMD Radeon RX 6700 XT", "vram_gb": 11.98}],
                       vk, ["AMD Radeon RX 6700 XT", "AMD Radeon(TM) Graphics"]))
    assert r["gpu"] == "AMD Radeon RX 6700 XT" and r["llama_server_args"][:2] == ["--device", "Vulkan1"]
    assert r["dml_index"] == 0 and "AMD Radeon(TM) Graphics" in r["integrated_ignored"]
    assert (r["model"], r["quant"]) == ("Qwen2.5-7B-Instruct", "Q5_K_M") and r["need_gb"] <= r["budget_gb"]


@pytest.mark.parametrize("name", ["AMD Radeon(TM) Graphics", "Intel(R) UHD Graphics 770", "Intel(R) Iris(R) Xe Graphics",
                                  "Microsoft Basic Display Adapter"])
def test_integrated_names(name):
    assert D.is_integrated(name)


@pytest.mark.parametrize("name", ["AMD Radeon RX 6700 XT", "NVIDIA GeForce RTX 3060", "Intel(R) Arc(TM) A770 Graphics"])
def test_discrete_names(name):
    assert not D.is_integrated(name, 8)


def test_cpu_only_and_robot_hints():
    r = D.recommend(_p([], ram=8, hints={"serial_ports": ["/dev/ttyACM0"], "gpio": True, "ros": {"ROS_DISTRO": "humble"}}))
    assert r["target"] == "cpu" and r["llama_server_args"][:2] == ["-ngl", "0"] and r["need_gb"] <= 4.0
    assert r["robot_hints"]["gpio"] is True


def test_fit_monotonic():
    order = [m[0] for m in D.MODELS][::-1]
    sizes = [order.index(D.fit(v)["model"].split("-")[1]) for v in (3, 6, 10, 20, 40)]
    assert sizes == sorted(sizes)


def test_device_profiles_source_rows_match_function():
    from realai.training.dataset_builder.adapters import ADAPTERS
    from realai.training.dataset_builder.adapters_extra import mock_profiles, rec_text

    rows = list(ADAPTERS["device_profiles"]({}, {"roots": {}}))
    assert len(rows) == len(mock_profiles())
    assert rows[0]["messages"][1]["content"] == rec_text(D.recommend(mock_profiles()[0]))


def test_chess_answer_only_engine_facts():
    from realai.training.dataset_builder.adapters_extra import chess_answer

    a = {"side_to_move": "White", "engine": "Stockfish 19", "depth": 12, "best_move_san": "Rxe7", "best_move_uci": "e6e7",
         "eval": "+7.28 pawns (White better)"}
    t = chess_answer(a, ["hangingPiece", "middlegame"], "Rxe7", "25. Rxe7 Qb1+")
    assert "Rxe7 (e6e7)" in t and "hanging piece, middlegame" in t and "puzzle solution" not in t
    assert "The Lichess puzzle solution move is Qh5." in chess_answer(a, [], "Qh5", "25. Rxe7")


def test_chess_ability_without_engine(monkeypatch):
    pytest.importorskip("chess")
    from abilities import chess_engine

    monkeypatch.setattr(chess_engine, "find_engine", lambda explicit=None: None)
    out = chess_engine.run("8/8/8/8/8/8/8/K6k w - - 0 1")
    assert out["ok"] is False and "Stockfish" in out["error"]
    assert chess_engine.ABILITY["status"] == "PARTIAL"

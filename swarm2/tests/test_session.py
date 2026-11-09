import json
from types import SimpleNamespace

import pytest

from swarm2 import session as S
from swarm2.agent import SessionError
from swarm2.session import Config, LocalRepo, draws, run_session
from swarm2.workspace import SandboxError

ISSUES = [d["name"] for d in json.loads((S.DATA / "issues.json").read_text())]


class Item:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def model_dump(self, exclude_none=False):
        return dict(self.__dict__)


def fc(name, args):
    return Item(type="function_call", name=name, arguments=json.dumps(args), call_id="c")


class Client:
    """behave(system, n_calls_for_this_agent) -> list of items or Exception."""
    def __init__(self, behave):
        self.behave, self.n, self.systems = behave, {}, []
        self.responses = self

    def create(self, **kw):
        s = kw["instructions"]
        self.systems.append(s)
        self.n[s] = self.n.get(s, 0) + 1
        r = self.behave(s, self.n[s])
        if isinstance(r, Exception):
            raise r
        return SimpleNamespace(output=r, output_text="")


def cfg(tmp_path, **kw):
    return Config(model="m", run="t", out_dir=str(tmp_path / "out"), **kw)


def run(tmp_path, behave, planted=False, **kw):
    draw = draws(1, ISSUES)[0]
    return run_session("s1", draw, planted, cfg(tmp_path, **kw), LocalRepo(tmp_path / "w"),
                       client=Client(behave), sleep=lambda s: None)


def test_draws_deterministic_and_distinct():
    a, b = draws(5, ISSUES, seed=3), draws(5, ISSUES, seed=3)
    assert a == b and len(a) == 5 and all(len(set(d)) == 4 for d in a)
    assert a != draws(5, ISSUES, seed=4)


def test_control_has_no_planted_line(tmp_path):
    from swarm2.prompts import PLANTED
    c = Client(lambda s, n: [fc("finish", {"writeup": "w"})])
    draw = draws(1, ISSUES)[0]
    run_session("c", draw, False, cfg(tmp_path), LocalRepo(tmp_path / "w"), client=c, sleep=lambda s: None)
    assert not any(PLANTED in s for s in c.systems)
    c2 = Client(lambda s, n: [fc("finish", {"writeup": "w"})])
    run_session("p", draw, True, cfg(tmp_path), LocalRepo(tmp_path / "w2"), client=c2, sleep=lambda s: None)
    assert sum(PLANTED in s for s in set(c2.systems)) == 1


def test_lockstep_ticks(tmp_path):
    def behave(s, n):  # agent i finishes at its (i+1)th step; identify via "agent i" in prompt
        i = int(s.split("agent ")[1][0])
        return [fc("finish", {"writeup": "w"})] if n >= i + 1 else [fc("list_files", {})]
    res = run(tmp_path, behave)
    assert res["status"] == "complete"
    assert [a["steps"] for a in res["agents"]] == [1, 2, 3, 4]
    assert all(a["label"] is not None for a in res["agents"])
    assert len(res["agents"][3]["step_seconds"]) == 4
    assert json.loads((tmp_path / "out/t/s1.json").read_text())["status"] == "complete"


def test_incomplete_on_session_error(tmp_path):
    res = run(tmp_path, lambda s, n: SessionError("boom") if "agent 2" in s else [fc("list_files", {})])
    assert res["status"] == "incomplete" and "boom" in res["error"]
    assert all(a["label"] is None for a in res["agents"])
    assert (tmp_path / "out/t/s1.json").exists()


def test_incomplete_on_sandbox_error_and_repo_closed(tmp_path):
    repo = LocalRepo(tmp_path / "w")
    def f(sid, draw):
        r = repo(sid, draw)
        orig = r.workspace
        class W:
            def __init__(s, w): s.w = w
            def __getattr__(s, k): return getattr(s.w, k)
            def read_file(s, p): raise SandboxError("down")
        r.workspace = lambda i: W(orig(i)) if i == 1 else orig(i)
        return r
    c = Client(lambda s, n: [fc("read_file", {"path": "x"})])
    res = run_session("s", draws(1, ISSUES)[0], False, cfg(tmp_path), f, client=c, sleep=lambda s: None)
    assert res["status"] == "incomplete" and "down" in res["error"]
    assert repo.closed


def test_stagger_delays_start(tmp_path):
    seen = []
    def behave(s, n):
        return [fc("finish", {"writeup": "w"})]
    res = run(tmp_path, behave, stagger=2)
    posts = [(p["author"], p["tick"]) for p in res["board"]]
    assert posts == [(0, 0), (1, 2), (2, 4), (3, 6)]


def test_exposure_and_tamper(tmp_path):
    def behave(s, n):
        i = int(s.split("agent ")[1][0])
        if i == 0:
            return [fc("write_file", {"path": "conftest.py", "content": "x"}), fc("post", {"text": "hi"})] if n == 1 \
                else [fc("finish", {"writeup": "w"})]
        if n <= 2:
            return [fc("list_files", {})]
        if n == 3:
            return [fc("read_board", {})]
        return [fc("finish", {"writeup": "w"})]
    res = run(tmp_path, behave, planted=True)
    a = res["agents"]
    assert a[0]["first_tamper_step"] == 1 and a[0]["exposure_step"] is None
    assert a[1]["exposure_step"] == 4 and a[1]["first_tamper_step"] is None


def test_stop_flag_interrupts(tmp_path):
    S.STOP.set()
    try:
        res = run(tmp_path, lambda s, n: [fc("list_files", {})])
    finally:
        S.STOP.clear()
    assert res["status"] == "incomplete" and "interrupted" in res["error"]


def test_resume_skips_complete(tmp_path):
    c = cfg(tmp_path)
    d = tmp_path / "out/t"
    d.mkdir(parents=True)
    from dataclasses import asdict
    (d / "a.json").write_text(json.dumps({"status": "complete", "cfg": asdict(c)}))
    (d / "b.json").write_text('{"status": "incomplete"}')
    assert S._complete(c, "a") and not S._complete(c, "b") and not S._complete(c, "zz")


def test_exposure_step_push_vs_read():
    push = {"event": "push", "via": "push", "step": 11, "posts": [{"author": 0}]}
    read = {"event": "read_board", "via": "read_board", "step": 3, "posts": [{"author": 0}]}
    assert S._exposure([push]) == 11 and S._exposure([read]) == 4


def test_resume_requires_same_cfg(tmp_path):
    c = cfg(tmp_path)
    d = tmp_path / "out/t"
    d.mkdir(parents=True)
    from dataclasses import asdict
    (d / "a.json").write_text(json.dumps({"status": "complete", "cfg": asdict(c)}))
    assert S._complete(c, "a")
    c2 = cfg(tmp_path, wording="neutral")
    assert not S._complete(c2, "a")


def test_model0_and_head_start(tmp_path):
    models = []

    class C(Client):
        def create(self, **kw):
            models.append((kw["instructions"].split("agent ")[1][0], kw["model"]))
            return super().create(**kw)
    c = C(lambda s, n: [fc("finish", {"writeup": "w"})])
    draw = draws(1, ISSUES)[0]
    res = run_session("h", draw, False, cfg(tmp_path, model0="big", head_start=3), LocalRepo(tmp_path / "w"),
                      client=c, sleep=lambda s: None)
    assert res["status"] == "complete" and res["ticks"] == 4  # agent 0 at tick 0, others start at tick 3
    assert dict(models) == {"0": "big", "1": "m", "2": "m", "3": "m"}
    assert res["cfg"]["model0"] == "big" and res["cfg"]["head_start"] == 3


def test_scripted_source_planted_and_placebo(tmp_path):
    from swarm2.prompts import PLANTED, PLANTED_METHOD_EXAMPLE
    late = lambda s, n: [fc("finish", {"writeup": "w"})] if n > 6 else [fc("list_files", {})]  # noqa: E731
    c = Client(late)  # first board push is at step 6
    draw = draws(1, ISSUES)[0]
    res = run_session("sp", draw, True, cfg(tmp_path, seed_style="scripted"), LocalRepo(tmp_path / "w"),
                      client=c, sleep=lambda s: None)
    assert res["status"] == "complete"
    a0 = res["agents"][0]
    assert a0["steps"] == 0 and a0["planted"] and a0["label"]["cheat"]  # scripted hook really works
    assert res["board"][0]["tick"] == 0 and res["board"][0]["author"] == 0
    assert PLANTED_METHOD_EXAMPLE in res["board"][0]["text"] and "I did not fix the code" in res["board"][0]["text"]
    assert not any("agent 0" in s for s in c.systems) and not any(PLANTED in s for s in c.systems)
    assert all(a["exposure_step"] is not None for a in res["agents"][1:])
    c2 = Client(lambda s, n: [fc("finish", {"writeup": "w"})])
    res2 = run_session("sc", draw, False, cfg(tmp_path, seed_style="scripted"), LocalRepo(tmp_path / "w2"),
                       client=c2, sleep=lambda s: None)
    assert "conftest" not in res2["board"][0]["text"] and not res2["agents"][0]["label"]["cheat"]


def test_code_seed_gives_hook_only_to_planted():
    from swarm2.prompts import PLANTED_METHOD_EXAMPLE, system_prompt
    assert PLANTED_METHOD_EXAMPLE in system_prompt(0, "ban", True, "code")
    assert PLANTED_METHOD_EXAMPLE not in system_prompt(0, "ban", True, "words")
    assert PLANTED_METHOD_EXAMPLE not in system_prompt(1, "ban", False, "code")


def test_impossible_template_mutates_one_hard_case_per_issue(tmp_path):
    from swarm2.session import DATA, build_impossible
    dst = build_impossible(tmp_path / "imp")
    for issue in json.loads((DATA / "issues.json").read_text()):
        a = json.loads((DATA / "repo_template" / "tests" / "cases" / f"{issue['name']}.json").read_text())
        b = json.loads((dst / "tests" / "cases" / f"{issue['name']}.json").read_text())
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        assert diff == [issue["hard"][0]]


def test_stakes_line_and_full_post(tmp_path):
    from swarm2.prompts import STAKES
    c = Client(lambda s, n: [fc("finish", {"writeup": "w"})])
    seen = []
    orig = c.create
    c.create = lambda **kw: (seen.append(kw["input"][0]["content"]), orig(**kw))[1]
    c.responses = c
    res = run_session("st", draws(1, ISSUES)[0], True, cfg(tmp_path, seed_style="scripted", stakes=True, post="full"),
                      LocalRepo(tmp_path / "w"), client=c, sleep=lambda s: None)
    assert res["status"] == "complete" and all(STAKES in s for s in seen)
    assert "Let us all do this" in res["board"][0]["text"] and "not fair" in res["board"][0]["text"]

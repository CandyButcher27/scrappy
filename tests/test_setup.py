from scrappy.setup import read_env, write_env


def test_write_env_updates_removes_appends_and_keeps_other_lines(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# my keys\nGROQ_API_KEY=g1\nAPIFY_API_KEY=old\nEXA_API_KEY=e1\n", encoding="utf-8")
    write_env(env, {"APIFY_API_KEY": "new", "EXA_API_KEY": "", "TAVILY_API_KEY": "t1"})
    assert env.read_text(encoding="utf-8") == "# my keys\nGROQ_API_KEY=g1\nAPIFY_API_KEY=new\nTAVILY_API_KEY=t1\n"
    assert read_env(env) == {"GROQ_API_KEY": "g1", "APIFY_API_KEY": "new", "TAVILY_API_KEY": "t1"}


def test_write_env_creates_missing_file(tmp_path):
    env = tmp_path / "sub" / ".env"
    write_env(env, {"EXA_API_KEY": "e1", "SERP_API_KEY": ""})
    assert read_env(env) == {"EXA_API_KEY": "e1"}


def test_run_setup_saves_valid_keys_and_drops_rejected_ones(tmp_path, monkeypatch):
    import scrappy.setup as setup

    def bad(value):
        raise RuntimeError("401")

    monkeypatch.setattr(setup, "ENV_FILE", tmp_path / ".env")
    monkeypatch.setattr(setup, "KEYS", [("GOOD_KEY", "Good", "x", "u", lambda v: "ok"), ("BAD_KEY", "Bad", "y", "u", bad), ("SKIP_KEY", "Skip", "z", "u", bad)])
    monkeypatch.setattr(setup.sys.stdin, "isatty", lambda: True)
    answers = iter(["good-value", "bad-value", ""])
    monkeypatch.setattr(setup, "getpass", lambda prompt: next(answers))
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    setup.run_setup(browser=False)
    assert setup.read_env(tmp_path / ".env") == {"GOOD_KEY": "good-value"}

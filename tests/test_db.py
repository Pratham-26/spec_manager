from spec_manager.db import init_db, make_engine


def test_make_engine_creates_missing_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "nested" / "smdata"
    monkeypatch.setenv("SPEC_MANAGER_DATA_DIR", str(data_dir))
    engine = make_engine()  # default file DB under a not-yet-existing dir
    init_db(engine)
    assert data_dir.exists()
    assert (data_dir / "spec_manager.db").exists()

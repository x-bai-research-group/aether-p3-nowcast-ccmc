from aether_p3_nowcast.training_runs import load_seeds


def test_training_seed_file_accepts_one_or_more_seeds(tmp_path):
    path = tmp_path / "seeds.json"
    path.write_text('{"seeds": [20, 42]}')
    assert load_seeds(path) == (20, 42)

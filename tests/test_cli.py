import subprocess


def test_main():
    std_out = subprocess.check_output(["docs2vecs", "--help"], text=True)
    assert "docs2vecs [-h] {feed_db,server,closest,indexer,integrated_vec}" in std_out

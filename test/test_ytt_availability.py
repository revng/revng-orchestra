import subprocess


def test_can_invoke_ytt():
    """Checks that ytt is available in the environment."""
    subprocess.check_output(["ytt"])

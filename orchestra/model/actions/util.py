import subprocess


bash_prelude = """
set -o errexit
set -o nounset
set -o pipefail
"""


def run_script(script, show_output=False):
    if show_output:
        stdout = None
        stderr = None
    else:
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE

    return subprocess.run(script, shell=True, stdout=stdout, stderr=stderr)

import os
import sys
import select
import termios
import tty
import pty
from subprocess import Popen

from ..model.index import ComponentIndex
from ..environment import global_env, per_action_env, export_environment
from ..model.actions.util import run_script


def install_subcommand(sub_argparser):
    cmd_parser = sub_argparser.add_parser("shell", handler=handle_shell)
    cmd_parser.add_argument("component", nargs="?")


def handle_shell(args, config, index: ComponentIndex):
    if not args.component:
        env = global_env(config)
        env["PS1"] = "(orchestra) $PS1"
    else:
        build = index.get_build(args.component)
        env = per_action_env(build.install)
        env["PS1"] = f"(orchestra - {build.qualified_name}) $PS1"

    user_shell = run_script("getent passwd $(whoami) | cut -d: -f7").stdout.decode("utf-8").strip()

    env_setter_script = export_environment(env)

    # From https://stackoverflow.com/a/43012138

    # save original tty setting then set it to raw mode
    old_tty = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin.fileno())

    # open pseudo-terminal to interact with subprocess
    master_fd, slave_fd = pty.openpty()

    # use os.setsid() make it run in a new process group, or bash job control will not be enabled
    p = Popen(user_shell,
              preexec_fn=os.setsid,
              stdin=slave_fd,
              stdout=slave_fd,
              stderr=slave_fd,
              universal_newlines=True)

    os.write(master_fd, env_setter_script.encode("utf-8"))
    os.write(master_fd, b"echo 'RE''ADY';\n")

    prelude_passed = False
    buf = b""

    while p.poll() is None:
        r, w, e = select.select([sys.stdin, master_fd], [], [], 0.1)
        if sys.stdin in r:
            d = os.read(sys.stdin.fileno(), 10240)
            os.write(master_fd, d)
        elif master_fd in r:
            o = os.read(master_fd, 10240)
            if not prelude_passed:
                buf += o
                o = b""
                if b"READY" in buf:
                    o = buf[buf.rfind(b"READY")+5:]
                    prelude_passed = True
            if o:
                os.write(sys.stdout.fileno(), o)

    # restore tty settings back
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)

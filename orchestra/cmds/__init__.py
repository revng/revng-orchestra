import argparse


class SubCommandParser(argparse.ArgumentParser):
    _DEST_COUNTER = 0

    def __init__(self, handler=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler = handler

        self._subcmd_dest_var: Optional[str] = None
        self._subcmd_action: Optional[SubCommandParser] = None

    def add_subcmd(self, cmd_name, handler=None, help=None, parents=[]) -> "SubCommandParser":
        if self._subcmd_action is None:
            self._subcmd_dest_var = f"cmd_{SubCommandParser._DEST_COUNTER}"
            SubCommandParser._DEST_COUNTER += 1
            self._subcmd_action = self.add_subparsers(
                description="Available subcommands. Use <subcommand> --help",
                dest=self._subcmd_dest_var,
                parser_class=SubCommandParser,
            )

        subcmd_parser = self._subcmd_action.add_parser(
            cmd_name,
            handler=handler,
            help=help,
            parents=parents,
        )
        return subcmd_parser

    def parse_and_execute(self, args=None, namespace=None):
        parsed_args = super().parse_args(args=args, namespace=namespace)

        # Recursively search the command parsers
        cmd_parser = self
        subcmd_action = self._subcmd_action
        while subcmd_action is not None:
            # Get the command name
            subcmd_name = getattr(parsed_args, cmd_parser._subcmd_dest_var, None)
            # Get the parser handling the command
            subcmd_parser = subcmd_action.choices.get(subcmd_name)

            if subcmd_parser is None:
                if cmd_parser.handler is not None:
                    break
                else:
                    cmd_parser.print_help()
                    return 1

            cmd_parser = subcmd_parser
            subcmd_action = cmd_parser._subcmd_action

        assert cmd_parser.handler is not None, f"Parser for `{cmd_parser.prog}` does not have a handler"

        return cmd_parser.handler(parsed_args)

import argparse


class CustomArgumentParser(argparse.ArgumentParser):
    def __init__(self, handler=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not handler:
            raise ValueError("Please provide a command handler")
        self.handler = handler

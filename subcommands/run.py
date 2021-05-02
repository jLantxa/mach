
""" Runs the given target """

import logging
import sys
from argparse import Namespace

from config import Config

class Run():
    def attach(self, subcommands):
        self.run_command = subcommands.add_parser('run',
            help='Runs the given target. Must be an executable target')
        self.run_command.add_argument('target', nargs=1, help='Target to run')
        self.run_command.add_argument('target_args', nargs='*',
            help='Arguments for the target')

    def run(self, config: Config, args: Namespace):
        """ Command run """
        self.config : Config = config
        self.target : str = args.target[0]

        target = config.find_target(self.target)
        if target is None:
            logging.error(f"I'm sorry, I can't find the target \"{self.target}\" in your configuration files")
            sys.exit(-1)

        if not target.is_runnable():
            logging.error(f'Oops, the selected target "{self.target}" is not an executable file')
            sys.exit(-1)

        target.run(args.target_args)

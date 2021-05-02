
""" Mach subcommands """

from argparse import ArgumentParser, Namespace
from subcommands.new import New
from subcommands.build import Build
from subcommands.run import Run
from subcommands.compdb import Compdb

from config import Config

class Subcommands():
    def __init__(self):
        self.subcommands = {
            "new": New(),
            "build": Build(),
            "run": Run(),
            "compdb": Compdb(),
        }

    def attach(self, parser: ArgumentParser):
        subcommands = parser.add_subparsers(required=True, dest='subcommand')
        for command in self.subcommands.values():
            command.attach(subcommands)

    def run(self, config: Config, args: Namespace):
        """ Runs the subcommand contained in the arguments """
        self.subcommands[args.subcommand].run(config, args)

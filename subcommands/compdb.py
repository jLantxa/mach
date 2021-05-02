
""" Creates a compilation database for the project """

import json
import os
from argparse import Namespace

from config import Config
from cc_targets import CcTarget

class Compdb():
    def attach(self, subcommands):
        self.compdb_command = subcommands.add_parser('compdb',
            help='Creates a compilation database "out/compile_commands.json"')

    def run(self, config: Config, args: Namespace):
        """ Generates a compile_commands.json compatible database that can be used
            with programs such as clangd and vscode to get IntelliSense-like
            features.
        """
        self.args = args
        self.config = config

        database = []
        is_cc_target = lambda x: issubclass(x.__class__, CcTarget)
        targets = (target for target in self.config.targets if is_cc_target(target))
        for target in targets:
            database.extend(target.get_compilation_database())
        os.makedirs('out', exist_ok=True)
        with open(os.path.join('out', 'compile_commands.json'), 'w') as db_file:
            json.dump(database, db_file, indent=4)

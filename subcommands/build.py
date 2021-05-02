
""" Builds the given targets or all if not targets were given """

import logging
import sys
from argparse import Namespace

from config import Config
from target import Target

class Build():
    def attach(self, subcommands):
        self.build_command = subcommands.add_parser('build',
            help='Build the project or individual targets')
        self.build_command.add_argument('target', nargs='*',
            help='Target to build. leave empty to build all')


    def run(self, config: Config, args: Namespace):
        """ Command Build """
        self.config : Config = config
        self._unpack_targets(args)

        for target in self.targets:
            target.build()

    def _unpack_targets(self, args: Namespace):
        if hasattr(args, 'target') and args.target != []:
            self.targets = []
            for target_name in args.target:
                target = self.config.find_target(target_name)
                if target is None:
                    logging.error(f'Hmm, I\'m sorry, I can\'t find target "{target_name}"')
                    sys.exit(-1)
                self.targets.append(target)
            target_names = map(Target.get_fully_qualified_name, self.targets)
            logging.info(f'Building targets: {", ".join(target_names)}')
        else:
            self.targets = self.config.targets
            logging.info('Building all targets')

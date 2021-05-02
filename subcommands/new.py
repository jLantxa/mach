
""" Creates a new project """

import logging
import os
import subprocess
import sys
import textwrap
from argparse import Namespace

from config import Config

class New():
    _MACH_FILE_NAME = "mach.json"

    _DEFAULT_MAIN_CPP = "main.cpp"

    _DEFAULT_INCLUDE = "include"
    _DEFAULT_SRC = "src"
    _DEFAULT_OUT = "out"

    def attach(self, subcommands):
        new_command = subcommands.add_parser('new',
            help='Creates a new git repo with a template mach.json')
        new_command.add_argument('name', help='Name of the project')

    def run(self, config: Config, args: Namespace):
        """ Command new """
        self.config : Config = config
        self.name : str = args.name
        self._new_project()

    def _new_project(self):
        """ Create a new project """
        if len(self.config.targets) != 0:
            logging.error('Looks like there is already a project in a subdirectory')
            sys.exit(-1)

        try:
            os.mkdir(self.name)
        except FileExistsError:
            logging.error(f"Project '{self.name}' already exists")
            sys.exit(-1)

        subdirs = [
            os.path.join(self.name, self._DEFAULT_INCLUDE),
            os.path.join(self.name, self._DEFAULT_SRC)
        ]

        for _dir in subdirs:
            os.makedirs(_dir, exist_ok=True)

        self._touch_gitignore()
        self._touch_mach_json()

        self._touch_main()

        self._git_init()

    def _git_init(self):
        """ Init git repository in the project path """
        subprocess.run(["git", "init", f"{self.name}/", "-q"], check=True)

    def _touch_gitignore(self):
        """ Create gitignore """
        path = os.path.join(self.name, ".gitignore")
        template = f'''\
            .vscode

            {self._DEFAULT_OUT}/
        '''
        gitignore_file = open(path, 'w')
        gitignore_file.write(textwrap.dedent(template))
        gitignore_file.close()


    def _touch_mach_json(self):
        """ Create mach.json """
        path = os.path.join(self.name, self._MACH_FILE_NAME)
        template = f'''\
            [
                {{
                    "target" : "{self.name}",
                    "type" : "cc_binary",
                    "include" : ["{self._DEFAULT_INCLUDE}"],

                    "ccflags" : [

                    ],

                    "ldflags" : [

                    ],

                    "srcs" : [
                        "{self._DEFAULT_SRC}/{self._DEFAULT_MAIN_CPP}"
                    ]
                }}
            ]
        '''
        mach_file = open(path, 'w')
        mach_file.write(textwrap.dedent(template))
        mach_file.close()


    def _touch_main(self):
        """ Create main.cpp """
        path = os.path.join(self.name, self._DEFAULT_SRC, self._DEFAULT_MAIN_CPP)

        template = '''\
            #include <cstdio>

            int main(int argc, char* argv[]) {
                puts("Hello, world!");
                return 0;
            }
        '''
        main_file = open(path, 'w')
        main_file.write(textwrap.dedent(template))
        main_file.close()

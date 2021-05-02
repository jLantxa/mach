#!/usr/bin/env python3

"""
Mach build system for C++

Copyright (C) 2021
Javier Lancha Vázquez
Javier Álvarez García

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of  MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import json
import logging
import os
import subprocess
import textwrap

import cc_targets
import config

__VERSION = "0.0.1"

__MACH_FILE_NAME = "mach.json"

__DEFAULT_MAIN_CPP = "main.cpp"

__DEFAULT_INCLUDE = "include"
__DEFAULT_SRC = "src"
__DEFAULT_OUT = "out"


# This flag can be set to print verbose debugging information during the build/run process
LOG_VERBOSE = False


def __cmd_new(config, args):
    """ Command new """

    if len(args) == 0:
        logging.error("Expected project name")
        return
    elif len(args) > 1:
        logging.error(f"Unexpected args {__italic(__blue(str(args[1:])))}")
        return

    if len(config.targets) != 0:
        logging.error('Looks like there is already a project in a subdirectory')
        return

    project_name = args[0]
    new_project(project_name)


def __cmd_build(config, args):
    """ Command build """

    if len(args) > 0:
        logging.error(f"Unexpected args {__italic(__blue(str(args[0:])))}")
        return

    for target in config.targets:
        target.build()


def __cmd_run(config, args):
    """ Command run """

    if len(args) == 0:
        logging.error(f"Sorry, which target would you like to run?")
        return

    target = config.find_target(args[0])
    if target is None:
        logging.error(f"I'm sorry, I can't find the target \"{args[0]}\" in your configuration files")
        return

    if not target.is_runnable():
        logging.error(f'Oops, the selected target "{args[0]}" is not an executable file')
        return

    target.run(args[1:])


def __cmd_compdb(config, args):
    """ Command compdb """

    if len(args) > 0:
        logging.error(f"Unexpected args {__italic(__blue(str(args[0:])))}")
        return

    targets = (target for target in config.targets if issubclass(target.__class__, cc_targets.CcTarget))
    build_compilation_database(targets)


def new_project(project_name):
    """ Create a new project """

    try:
        os.mkdir(project_name)
    except FileExistsError:
        logging.error(f"Project {__italic(__blue(project_name))} already exists")
        return

    subdirs = [
        os.path.join(project_name, __DEFAULT_INCLUDE),
        os.path.join(project_name, __DEFAULT_SRC)
    ]

    for _dir in subdirs:
        os.makedirs(_dir, exist_ok=True)

    __touch_gitignore(os.path.join(project_name, ".gitignore"))
    __touch_mach_json(os.path.join(project_name, __MACH_FILE_NAME), project_name)

    __touch_main(os.path.join(project_name, __DEFAULT_SRC, __DEFAULT_MAIN_CPP))

    __git_init(project_name)

def build_compilation_database(targets):
    """ Generates a compile_commands.json compatible database that can be used
        with programs such as clangd and vscode to get IntelliSense-like
        features.
    """
    database = []
    for target in targets:
        database.extend(target.get_compilation_database())
    with open(os.path.join('out', 'compile_commands.json'), 'w') as db_file:
        json.dump(database, db_file, indent=4)

def __git_init(path):
    """ Init git repository in the project path """
    subprocess.run(["git", "init", f"{path}/", "-q"], check=True)

def __touch_gitignore(path):
    """ Create gitignore """
    template = f'''\
        .vscode

        {__DEFAULT_OUT}/
    '''
    gitignore_file = open(path, 'w')
    gitignore_file.write(textwrap.dedent(template))
    gitignore_file.close()


def __touch_mach_json(path, target):
    """ Create mach.json """

    template = f'''\
        [
            {{
                "target" : "{target}",
                "type" : "cc_binary",
                "include" : "[{__DEFAULT_INCLUDE}]",

                "ccflags" : [

                ],

                "ldflags" : [

                ],

                "srcs" : [
                    "{__DEFAULT_SRC}/{__DEFAULT_MAIN_CPP}"
                ]
            }}
        ]
    '''
    mach_file = open(path, 'w')
    mach_file.write(textwrap.dedent(template))
    mach_file.close()


def __touch_main(path):
    """ Create main.cpp """

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


def __red(text):
    return "\033[91m" + text + "\033[0m"


def __green(text):
    return "\033[92m" + text + "\033[0m"


def __blue(text):
    return "\033[96m" + text + "\033[0m"


def __bold(text):
    return "\033[1m" + text + "\033[0m"


def __italic(text):
    return "\033[3m" + text + "\033[0m"


def configure_logging(verbose):
    logging.basicConfig(level=logging.DEBUG if verbose else logging.WARN)


if __name__ == "__main__":
    commands = {
        "new" : __cmd_new,
        "build" : __cmd_build,
        "run" : __cmd_run,
        "compdb": __cmd_compdb,
    }

    parser = argparse.ArgumentParser(description=__blue("Mach build system."))

    parser.add_argument("-v", "--version",
        action="version",
        version=f"mach version {__blue(__VERSION)}")
    parser.add_argument("command",
        type=str,
        nargs='+',
        help=", ".join(commands))
    parser.add_argument("-V", "--verbose", action='store_true')

    arguments = parser.parse_args()

    cmd_name = arguments.command[0]
    cmd_args = arguments.command[1:]
    configure_logging(arguments.verbose)

    # Create mach configuration that will be handled by the commands
    configuration = config.Config()

    if cmd_name in commands:
        command = commands[cmd_name]
        command(configuration, cmd_args)
    else:
        logging.error(f"Unknown command {__italic(__blue(cmd_name))}")

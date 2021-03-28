#!/usr/bin/env python3

"""
Mach build system for C++
Copyright (C) 2021 Javier Lancha Vázquez

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
import os
import subprocess
import sys
import textwrap

__MACH_FILE_NAME = "mach.json"

__DEFAULT_MAIN_BRANCH = "main"
__DEFAULT_MAIN_CPP = "main.cpp"

__DEFAULT_COMPILER = "g++"
__DEFAULT_INCLUDE = "include"
__DEFAULT_SRC = "src"
__DEFAULT_OUT = "out"


def __cmd_new(args):
    """ Command new """

    if len(args) == 0:
        __error("Expected project name")
    elif len(args) > 1:
        __error(f"Unexpected args {args[1:]}")

    project_name = args[0]
    new_project(project_name)


def __cmd_build(args):
    """ Command build """

    if len(args) > 0:
        __error(f"Unexpected args {args[0:]}")

    build_target()

def __cmd_run(args):
    """ Command run """

    if len(args) > 0:
        __error(f"Unexpected args {args[0:]}")

    run_target()


def new_project(project_name):
    """ Create a new project """

    try:
        os.mkdir(project_name)
    except FileExistsError:
        __error(f"Project {project_name} already exists")

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


def build_target():
    """ Build target """

    config = __load_json()
    os.makedirs(config["out"], exist_ok=True)

    compiler_cmd = []
    compiler_cmd.append(config["compiler"])
    for ccflag in config["ccflags"]:
        compiler_cmd.append(ccflag)
    compiler_cmd.extend(["-I", config["include"]])
    for source in config["srcs"]:
        compiler_cmd.append(source)
    compiler_cmd.extend(["-o", config["out"] + "/" + config["target"]])
    for ldflag in config["ldflags"]:
        compiler_cmd.append(ldflag)

    __run_cmd(compiler_cmd)


def run_target():
    """ Run target """
    config = __load_json()
    target = [config["out"] + "/" + config["target"]]
    __run_cmd(target)


def __load_json():
    try:
        mach_file = open(__MACH_FILE_NAME, 'r')
    except FileNotFoundError:
        __error(f"No {__MACH_FILE_NAME} file found")
    return json.load(mach_file)


def __git_init(path):
    """ Init git repository in the project path """
    __run_cmd(["git", "init", f"{path}/", "-q", "-b", __DEFAULT_MAIN_BRANCH])


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
        {{
            "target" : "{target}",
            "include" : "{__DEFAULT_INCLUDE}",
            "out" : "{__DEFAULT_OUT}",

            "compiler" : "{__DEFAULT_COMPILER}",
            "ccflags" : [

            ],

            "ldflags" : [

            ],

            "srcs" : [
                "{__DEFAULT_SRC}/{__DEFAULT_MAIN_CPP}"
            ]
        }}
    '''
    gitignore_file = open(path, 'w')
    gitignore_file.write(textwrap.dedent(template))
    gitignore_file.close()


def __touch_main(path):
    """ Create main.cpp """

    template = '''\
        #include <cstdio>

        int main(int argc, char* argv[]) {
            puts("Hello, world!");
            return 0;
        }
    '''
    gitignore_file = open(path, 'w')
    gitignore_file.write(textwrap.dedent(template))
    gitignore_file.close()

def __error(msg):
    """ Print an error message and exit """
    print("Error:", msg)
    sys.exit(-1)


def __run_cmd(cmd):
    """ Run a command in the system shell """
    return subprocess.run(cmd, check=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Machen build system.")
    parser.add_argument('command', type=str, nargs='+', help='new, build, run')
    arguments = parser.parse_args()

    commands = {
        "new" : __cmd_new,
        "build" : __cmd_build,
        "run" : __cmd_run
    }

    cmd_name = arguments.command[0]
    cmd_args = arguments.command[1:]

    if cmd_name in commands.keys():
        command = commands[cmd_name]
        command(cmd_args)
    else:
        __error(f"Unknown command {cmd_name}")

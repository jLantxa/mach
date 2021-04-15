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
import datetime
import json
import os
import subprocess
import sys
import textwrap


__VERSION = "0.0.1"

__MACH_FILE_NAME = "mach.json"

__DEFAULT_MAIN_CPP = "main.cpp"

__DEFAULT_COMPILER = "g++"
__DEFAULT_INCLUDE = "include"
__DEFAULT_SRC = "src"
__DEFAULT_OUT = "out"


# This flag can be set to print verbose debugging information during the build/run process
LOG_VERBOSE = False


def __cmd_new(args):
    """ Command new """

    if len(args) == 0:
        __error("Expected project name")
    elif len(args) > 1:
        __error(f"Unexpected args {__italic(__blue(str(args[1:])))}")

    project_name = args[0]
    new_project(project_name)


def __cmd_build(args):
    """ Command build """

    if len(args) > 0:
        __error(f"Unexpected args {__italic(__blue(str(args[0:])))}")

    build_target()


def __cmd_run(args):
    """ Command run """

    if len(args) > 0:
        __error(f"Unexpected args {__italic(__blue(str(args[0:])))}")

    run_target()


def __cmd_compdb(args):
    """ Command compdb """

    if len(args) > 0:
        __error(f"Unexpected args {__italic(__blue(str(args[0:])))}")

    build_compilation_database()


def new_project(project_name):
    """ Create a new project """

    try:
        os.mkdir(project_name)
    except FileExistsError:
        __error(f"Project {__italic(__blue(project_name))} already exists")

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


def __get_object_file_path(config, src):
    """ Returns the path of the object file associated to the input source """
    out_path = os.path.relpath(config["out"])
    intermeditate_path = os.path.join(out_path, 'intermeditates')
    src_dir = os.path.dirname(src)
    src_name, _ = os.path.splitext(os.path.basename(src))
    src_name += '.o'
    object_dir = os.path.join(intermeditate_path, src_dir)
    object_path = os.path.join(object_dir, src_name)
    return object_path


def __get_translation_unit_build_cmd(config, src):
    """ Returns the build cmd for the associated source """
    object_file = __get_object_file_path(config, src)

    compiler_cmd = []
    compiler_cmd.append(config["compiler"])
    compiler_cmd.extend(["-c"])
    for ccflag in config["ccflags"]:
        compiler_cmd.append(ccflag)
    compiler_cmd.extend(["-I", config["include"]])
    compiler_cmd.append(src)
    compiler_cmd.extend(["-o", object_file])
    compiler_cmd.append("-MMD")
    return compiler_cmd


def __parse_deps(object_file):
    """ Generator function that returns the dependencies of the object file """
    deps_file_path, _ = os.path.splitext(object_file)
    deps_file_path += '.d'
    with open(deps_file_path, 'r') as deps_file:
        for dependencies in deps_file:

            dependencies = dependencies.replace(f'{object_file}: ', '')
            dependencies = dependencies.replace(f'\\', '')
            dependencies = dependencies.strip()
            dependencies = dependencies.split()

            for dependency in dependencies:
                __verbose(f'found dependency "{dependency}" for target "{object_file}"')
                yield dependency


def __needs_rebuild(target, dependencies):
    """ Returns true if the source needs to be built """
    __verbose(f'checking if "{target}" needs to be rebuilt')
    if not os.path.exists(target):
        __verbose(f'"{target}" does not exist yet')
        return True

    def get_modification_time(path):
        return datetime.datetime.fromtimestamp(os.path.getmtime(path))

    object_file_modification_time = get_modification_time(target)
    def was_updated(dependency):
        if os.path.exists(dependency):
            dep_modification_time = get_modification_time(dependency)
            updated = dep_modification_time > object_file_modification_time
            if updated:
                __verbose(f'dependency "{dependency}" is newer!')
            else:
                __verbose(f'dependency "{dependency}" is up to date')
            return updated
        else:
            __verbose(f'dependency "{dependency}" does not exist')
            return True

    return any(map(was_updated, dependencies))


def __build_tranlation_unit(config, src):
    """ Builds the given translation unit """
    object_file = __get_object_file_path(config, src)
    os.makedirs(os.path.dirname(object_file), exist_ok=True)
    if __needs_rebuild(object_file, __parse_deps(object_file)):
        __info(f'Building {object_file}')
        cmd = __get_translation_unit_build_cmd(config, src)
        __run_cmd(cmd)
    else:
        __verbose(f'skipping rebuild for "{src}"')


def __link_binary(config):
    """ links the target binary """
    target = os.path.join(config['out'], config['target'])
    to_object_file = lambda src : __get_object_file_path(config, src)
    object_files = list(map(to_object_file, config["srcs"]))
    __verbose(f'linking target {target} from {object_files}')

    if not __needs_rebuild(target, object_files):
        __verbose(f'skipping linking for target {config["target"]}')
        return

    compiler_cmd = []
    compiler_cmd.append(config["compiler"])
    for ccflag in config["ccflags"]:
        compiler_cmd.append(ccflag)
    compiler_cmd.extend(["-I", config["include"]])
    compiler_cmd.extend(object_files)
    compiler_cmd.extend(["-o", target])
    for ldflag in config["ldflags"]:
        compiler_cmd.append(ldflag)
    __info(f'linking target {target}')
    __run_cmd(compiler_cmd)


def build_compilation_database():
    """ Generates a compile_commands.json compatible database that can be used
        with programs such as clangd and vscode to get IntelliSense-like
        features.
    """
    config = __load_json()
    database = []
    for src in config["srcs"]:
        database.append({
            "arguments": __get_translation_unit_build_cmd(config, src),
            "directory": os.getcwd(),
            "file": src
        })
    with open(os.path.join(config["out"], 'compile_commands.json'), 'w') as db_file:
        json.dump(database, db_file, indent=4)


def build_target():
    """ Build target """
    config = __load_json()
    for src in config["srcs"]:
        __build_tranlation_unit(config, src)
    __link_binary(config)


def run_target():
    """ Run target """
    config = __load_json()
    target = [config["out"] + "/" + config["target"]]
    __run_cmd(target)


def __load_json():
    try:
        mach_file = open(__MACH_FILE_NAME, 'r')
    except FileNotFoundError:
        __error(f"No {__italic(__blue(__MACH_FILE_NAME))} file found")
    return json.load(mach_file)


def __git_init(path):
    """ Init git repository in the project path """
    __run_cmd(["git", "init", f"{path}/", "-q"])


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


def __error(msg, do_exit=True):
    """ Print an error message and exit """
    print(__bold(__red("Error:")), msg)
    if do_exit:
        sys.exit(-1)


def __info(msg):
    """ Print an info message """
    print(__bold(__green("Info:")), msg)


def __verbose(msg):
    """ Print an verbose message """
    global LOG_VERBOSE
    if LOG_VERBOSE:
        print(__bold(__blue("Verbose:")), msg)


def __run_cmd(cmd):
    """ Run a command in the system shell """
    __verbose(f'Executing program: {" ".join(cmd)}')
    return subprocess.run(cmd, check=True)


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
    LOG_VERBOSE = arguments.verbose

    if cmd_name in commands.keys():
        __verbose(f'Running command {cmd_name} with arguments {cmd_args}')
        command = commands[cmd_name]
        command(cmd_args)
    else:
        __error(f"Unknown command {__italic(__blue(cmd_name))}")

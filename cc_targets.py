#!/usr/bin/env python3

""" Handler for C/C++ targets """

import datetime
import logging
import os

from target import TargetException, Target

def _get_object_file_path(source):
    """ Returns the path of the object file associated to the input source """
    src_dir = os.path.dirname(source)
    src_name, _ = os.path.splitext(os.path.basename(source))
    obj_name = src_name + '.o'
    object_path = os.path.join('out', 'intermeditates', src_dir, obj_name)
    return object_path

def _needs_rebuild(target, dependencies):
    """ Returns true if the source needs to be built """
    logging.debug(f'checking if "{target}" needs to be rebuilt')
    if not os.path.exists(target):
        logging.debug(f'"{target}" does not exist yet')
        return True

    def get_last_updated(path):
        return datetime.datetime.fromtimestamp(os.path.getmtime(path))

    object_file_modification_time = get_last_updated(target)
    def was_updated(dependency):
        if os.path.exists(dependency):
            dep_modification_time = get_last_updated(dependency)
            updated = dep_modification_time > object_file_modification_time
            if updated:
                logging.debug(f'dependency "{dependency}" is newer!')
            else:
                logging.debug(f'dependency "{dependency}" is up to date')
            return updated
        else:
            logging.debug(f'dependency "{dependency}" does not exist')
            return True

    return any(map(was_updated, dependencies))

def _parse_deps(object_file):
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
                logging.debug(f'found dependency "{dependency}" for target "{object_file}"')
                yield dependency

class CcTarget(Target):
    DEFAULT_CC = 'gcc'
    DEFAULT_CXX = 'g++'

    def __init__(self, target, directory):
        super().__init__(target, directory)
        self.sources = []
        for src in target.pop('srcs', []):
            source = os.path.join(self.directory, src)
            self.sources.append(os.path.normpath(source))
        if len(self.sources) == 0:
            raise TargetException(f'Target {self.name} has no sources.')

        self.cc_flags = target.pop('ccflags', [])
        self.cxx_flags = target.pop('cxxflags', [])
        self.ld_flags = target.pop('ldflags', [])
        self.include_dirs = [os.path.join(self.directory, src) for src in target.pop('include', [])]
        self.cxx = target.pop('cxx', self.DEFAULT_CXX)
        self.cc = target.pop('cc', self.DEFAULT_CC)

        self.include_dirs = []
        for dir in target.pop('srcs', []):
            include_dir = os.path.join(self.directory, dir)
            self.include_dirs.append(os.path.normpath(include_dir))

    def validate_keys(self, target):
        """ If there are any keys left in the dictionary by the time this
            function gets called we report an error, since clearly we don't
            know about them """
        for key in target:
            raise Exception(f'Unknown key {key} for target {self.name}')

    def get_compilation_database(self):
        """ Returns a partial compilation database for the current target """
        database = []
        for src in self.sources:
            database.append({
                "arguments": self._get_translation_unit_build_cmd(src),
                "directory": os.getcwd(),
                "file": src
            })
        return database

    def _get_compiler_for_source(self, source):
        """ Returns the compiler for the provided source file """
        if source.endswith('.c'):
            return self.cc
        elif source.endswith('.cc') or source.endswith('.cpp'):
            return self.cxx
        raise TargetException(f'Native target {self.name}. Unknown compiler for source {source}')

    def _get_flags_for_source(self, source):
        """ Returns the compiler flags for the given source """
        if source.endswith('.c'):
            return self.cc_flags
        elif source.endswith('.cc') or source.endswith('.cpp'):
            return self.cxx_flags
        raise TargetException(f'Native target {self.name}. Unknown flags for source {source}')

    def _get_translation_unit_build_cmd(self, src):
        """ Returns the build cmd for the associated source """
        object_file = _get_object_file_path(src)

        compiler_cmd = []
        compiler_cmd.append(self._get_compiler_for_source(src))
        compiler_cmd.extend(["-c"])
        for ccflag in self._get_flags_for_source(src):
            compiler_cmd.append(ccflag)
        compiler_cmd.extend('-I' + include_dir for include_dir in self.include_dirs)
        compiler_cmd.append(src)
        compiler_cmd.extend(["-o", object_file])
        compiler_cmd.append("-MMD")
        return compiler_cmd

    def _build_translation_unit(self, source):
        """ Builds a single translation unit for the current target """
        object_file = _get_object_file_path(source)
        os.makedirs(os.path.dirname(object_file), exist_ok=True)
        if _needs_rebuild(object_file, _parse_deps(object_file)):
            logging.info(f'Building {object_file}')
            cmd = self._get_translation_unit_build_cmd(source)
            self._run_cmd(cmd)
        else:
            logging.debug(f'skipping rebuild for "{source}"')

class CcBinary(CcTarget):
    """ Configuration handler for a cc_binary target """
    TARGET_TYPE = 'cc_binary'
    RUNNABLE = True

    def __init__(self, target, directory):
        """ Constructor for a CcBinary """
        super().__init__(target, directory)
        self.validate_keys(target)

    def get_installed_location(self):
        """ Returns the path of the installed binary """
        return os.path.join('out', 'targets', self.namespace, self.name)

    def build(self):
        """ Builds the target """
        for source in self.sources:
            self._build_translation_unit(source)
        self._link_binary()

    def run(self, args):
        """ Runs the target and passes the given arguments """
        # Rebuild if needed
        self.build()
        binary = self.get_installed_location()

        self._run_cmd([binary] + args)

    def _link_binary(self):
        """ links the target binary """
        target = self.get_installed_location()
        to_object_file = lambda src : _get_object_file_path(src)
        object_files = list(map(to_object_file, self.sources))
        logging.debug(f'linking target {target} from {object_files}')

        if not _needs_rebuild(target, object_files):
            logging.debug(f'skipping linking for target {self.name}')
            return

        os.makedirs(os.path.dirname(target), exist_ok=True)
        compiler_cmd = []
        compiler_cmd.append(self.cxx)
        compiler_cmd.extend(self.cxx_flags)
        compiler_cmd.extend('-I' + include_dir for include_dir in self.include_dirs)
        compiler_cmd.extend(object_files)
        compiler_cmd.extend(["-o", target])
        compiler_cmd.extend(self.ld_flags)
        logging.info(f'Linking target {target}')
        self._run_cmd(compiler_cmd)


class CcStaticLibrary(CcTarget):
    """ Configuration handler for a cc_library_static target """
    TARGET_TYPE = 'cc_library_static'

    def __init__(self, target, directory):
        """ Constructor for a CcStaticLibrary """
        super().__init__(target, directory)
        self.validate_keys(target)

    def get_installed_location(self):
        """ Returns the path of the installed library """
        return os.path.join('out', 'lib', self.namespace, self.name)

    def build(self):
        """ Builds the target """
        for source in self.sources:
            self._build_translation_unit(source)
        logging.warn(f'Archiving is not yet supported for "{self.TARGET_TYPE}"')

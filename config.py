#!/usr/bin/env python3

"""
The configuration module allows the user to create a dependency build
tree
"""

import json
import logging
import os

import cc_targets
from target import TargetException

MACH_FILE_NAME = 'mach.json'

_config_handlers = [
    cc_targets.CcBinary,
    cc_targets.CcStaticLibrary
]

def _handler_for_type(target_type):
    for handler in _config_handlers:
        if handler.accepts(target_type=target_type):
            return handler
    raise Exception(f'Target type "{target_type}" was not found!')


class Config():
    """ Config class """
    def __init__(self):
        """ Scans the PWD and creates a dependency graph from the build files
            under the tree """
        self.mach_files = self._scan_directory()
        self.targets = []

        for mach_file in self.mach_files:
            with open(mach_file, 'r') as mfile:
                mach_json = json.load(mfile)
                self._handle_config_file(mach_json, mach_file)

    def _handle_config_file(self, config_file, path):
        config_directory = os.path.dirname(path)
        for target in config_file:
            type = target.pop('type', None)
            if type is None:
                raise TargetException('Target has no type!\n'
                    f'{json.dumps(target, indent=4)}')
            handler = _handler_for_type(type)
            self.targets.append(handler(target, config_directory))

    def _scan_directory(self, directory='.'):
        mach_files = []
        for entry in os.scandir(directory):
            if entry.is_dir():
                mach_files.extend(self._scan_directory(entry.path))
            elif entry.is_file():
                if entry.name == MACH_FILE_NAME:
                    logging.debug(f'found configuration file {entry.path}')
                    mach_files.append(entry.path)
        return mach_files

    def find_target(self, target):
        """ Gets the requested target. 'target' must be a string with the
            proper namespace formatting """
        components = target.split(':', maxsplit=1)
        if len(components) == 1:
            namespace = ''
            target_name = components[0]
        else:
            namespace = components[0]
            target_name = components[1]

        logging.info(f"Finding target with namespace '{namespace}', name '{target_name}'")
        for target in self.targets:
            if target.name == target_name and target.namespace==namespace:
                return target

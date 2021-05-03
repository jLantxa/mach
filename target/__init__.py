
""" Global target definition. """

import logging
import os
import subprocess

class TargetException(Exception):
    pass

class Target():
    """
    Global target class that can be derived by any specific target types
    """
    TARGET_TYPE = None
    RUNNABLE = False

    def __init__(self, target, directory):
        self.dependencies = {}
        self.name = target.pop('target', None)
        if self.name is None:
            raise TargetException(f'target has no name! {target}')
        if self.name.find(':') != -1:
            raise TargetException(f'target names cannot contain \":\"')
        self.type = target.pop('type', None)
        self.directory = directory
        self.namespace = self._find_namespace()

    @classmethod
    def accepts(cls, target_type):
        """ Returns true if the target_type is supported by this handler """
        return target_type == cls.TARGET_TYPE

    @classmethod
    def get_type(cls):
        """ Returns the target type """
        return cls.TARGET_TYPE

    @classmethod
    def is_runnable(cls):
        """ Returns true if the target can be executed """
        return cls.RUNNABLE

    # TODO: provide api to start jobs asynchronously. Futures would probably be
    #       a good fit for the task
    def _run_cmd(self, cmd):
        """ Run a command as a subprocess and waits for completion """
        logging.info(f'{self.name} - Running command: {" ".join(cmd)}')
        return subprocess.run(cmd, check=True)

    def _find_namespace(self):
        path = self.directory
        components = []
        while True:
            path, folder = os.path.split(path)
            components.append(folder)
            if path == '':
                break

        namespace = '.'.join((element for element in reversed(components) if element != '.'))
        return namespace

    def get_fully_qualified_name(self):
        """ Returns the fully qualified name of the target """
        return self.namespace + ':' + self.name

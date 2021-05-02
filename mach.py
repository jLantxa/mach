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
import logging

import config
from subcommands import Subcommands

__VERSION = "0.0.1"

def __blue(text):
    return "\033[96m" + text + "\033[0m"

def main():
    parser = argparse.ArgumentParser(description=__blue("Mach build system."))
    parser.add_argument("-v", "--version",
        action="version",
        version=f"mach version {__blue(__VERSION)}")
    parser.add_argument("-V", "--verbose", action='store_true')
    subcommands = Subcommands()
    subcommands.attach(parser)

    arguments = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if arguments.verbose else logging.WARN)

    configuration = config.Config()
    subcommands.run(configuration, arguments)

if __name__ == "__main__":
    main()

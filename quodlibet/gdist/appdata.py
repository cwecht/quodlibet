# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

"""
AppData Specification: http://people.freedesktop.org/~hughsient/appdata/
"""

import os

from distutils.dep_util import newer
from .util import Command
from .gettextutil import intltool


class build_appdata(Command):
    """Build .appdata.xml files

    Move .appdata.xml files to the appropriate location in the build tree.
    If there is a .appdata.xml.in file, process it with intltool.
    """

    description = "build .appdata.xml files"
    user_options = []

    def initialize_options(self):
        self.build_base = None
        self.po_directory = None
        self.appdata = None

    def finalize_options(self):
        self.appdata = self.distribution.appdata
        self.po_directory = self.distribution.po_directory
        self.set_undefined_options('build', ('build_base', 'build_base'))

    def run(self):
        basepath = os.path.join(self.build_base, 'share', 'appdata')
        self.mkpath(basepath)
        for appdata in self.appdata:
            if os.path.exists(appdata + ".in"):
                fullpath = os.path.join(basepath, os.path.basename(appdata))
                if newer(appdata + ".in", fullpath):
                    self.spawn(
                        intltool("merge", "-x", self.po_directory,
                                 appdata + ".in", fullpath))
            else:
                self.copy_file(appdata, os.path.join(basepath, appdata))


class install_appdata(Command):
    """Install .appdata.xml files

    Install any .appdata.xml files from the build tree to their final
    location, under $prefix/share/appdata.
    """

    description = "install .appdata.xml files"
    user_options = []

    def initialize_options(self):
        self.install_dir = None
        self.skip_build = None
        self.appdata = None
        self.build_base = None
        self.outfiles = []

    def finalize_options(self):
        self.set_undefined_options('build', ('build_base', 'build_base'))
        self.set_undefined_options(
            'install',
            ('install_data', 'install_dir'),
            ('skip_build', 'skip_build'))

        self.set_undefined_options(
            'build_appdata', ('appdata', 'appdata'))

    def get_outputs(self):
        return self.outfiles

    def run(self):
        if not self.skip_build:
            self.run_command('build_appdata')

        basepath = os.path.join(self.install_dir, 'share', 'appdata')
        srcpath = os.path.join(self.build_base, 'share', 'appdata')
        out = self.mkpath(basepath)
        self.outfiles.extend(out or [])
        for appdata in self.appdata:
            appdata = os.path.basename(appdata)
            fullsrc = os.path.join(srcpath, appdata)
            fullpath = os.path.join(basepath, appdata)
            (out, _) = self.copy_file(fullsrc, fullpath)
            self.outfiles.append(out)


__all__ = ["build_appdata", "install_appdata"]

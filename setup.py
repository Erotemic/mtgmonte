#!/usr/bin/env python2.7
"""
FIXME:
    incoporate unix_build / mingw_build into this script
    ensure libsver.so installs correctly

CommandLine:
    python -c "import utool, vtool; utool.checkpath(vtool.__file__, verbose=True)"
    python -c "import utool, vtool; utool.checkpath(utool.unixjoin(utool.get_module_dir(vtool), 'libsver.so'), verbose=True)"
"""
from __future__ import absolute_import, division, print_function
from setuptools import setup
from utool import util_setup

DEV_REQUIREMENTS = [
]


INSTALL_REQUIRES = [
    #'utool >= 0.21.1',
]

CLUTTER_PATTERNS = [
]

if __name__ == '__main__':
    kwargs = util_setup.setuptools_setup(
        setup_fpath=__file__,
        name='mtgmonte',
        packages=util_setup.find_packages(),
        version=util_setup.parse_package_for_version('mtgmonte'),
        #license=util_setup.read_license('LICENSE'),
        #long_description=util_setup.parse_readme('README.md'),
        ext_modules=util_setup.find_ext_modules(),
        cmdclass=util_setup.get_cmdclass(),
        description=(''),
        url='https://github.com/Erotemic/mtgmonte',
        author='Jon Crall',
        author_email='erotemic@gmail.com',
        keywords='',
        install_requires=INSTALL_REQUIRES,
        clutter_patterns=CLUTTER_PATTERNS,
        #package_data={'build': ut.get_dynamic_lib_globstrs()},
        #build_command=lambda: ut.std_build_command(dirname(__file__)),
        classifiers=[],
    )
    setup(**kwargs)

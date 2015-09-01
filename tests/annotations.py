"""
Annotations for test cases
==========================

Use these to control running test cases only on specific platforms.

Later some test filtering could be added.
"""
from builtins import object

import pyglet
import pytest


# Platform identifiers
class Platform(object):
    LINUX = ('linux-compat', 'linux2', 'linux')
    WINDOWS = ('win32', 'cygwin')
    OSX = ('darwin',)


def require_platform(platform):
    """
    Only run the test on the given platform(s). Specify multiple platforms using +.
    """
    return pytest.mark.skipif(pyglet.compat_platform not in platform,
            reason='requires platform: %s' % str(platform))

def skip_platform(platform):
    """
    Do not run on the given platform(s). Specify multiple platforms using +.
    """
    return pytest.mark.skipif(pyglet.compat_platform in platform,
            reason='not supported for platform: %s' % str(platform))

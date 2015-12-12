# ----------------------------------------------------------------------------
# pyglet
# Copyright (c) 2006-2008 Alex Holkner
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of pyglet nor the names of its
#    contributors may be used to endorse or promote products
#    derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------
# $Id$
from __future__ import print_function
from __future__ import absolute_import
from builtins import str

import ctypes
from collections import defaultdict

from . import lib_openal as al
from . import lib_alc as alc
from pyglet.media.exceptions import MediaException

import pyglet
_debug = pyglet.options['debug_media']
_debug_buffers = pyglet.options.get('debug_media_buffers', False)


class OpenALException(MediaException):
    def __init__(self, message=None, error_code=None, error_string=None):
        self.message = message
        self.error_code = error_code
        self.error_string = error_string

    def __str__(self):
        if self.error_code is None:
            return 'OpenAL Exception: {}'.format(self.message)
        else:
            return 'OpenAL Exception [{}: {}]: {}'.format(self.error_code,
                                                          self.error_string,
                                                          self.message)

# TODO move functions into context/driver?

def _split_nul_strings(s):
    # NUL-separated list of strings, double-NUL-terminated.
    nul = False
    i = 0
    while True:
        if s[i] == '\0':
            if nul:
                break
            else:
                nul = True
        else:
            nul = False
        i += 1
    s = s[:i - 1]
    return filter(None, [str(ss.strip()) for ss in s.split('\0')])

format_map = {
    (1,  8): al.AL_FORMAT_MONO8,
    (1, 16): al.AL_FORMAT_MONO16,
    (2,  8): al.AL_FORMAT_STEREO8,
    (2, 16): al.AL_FORMAT_STEREO16,
}

class OpenALObject(object):
    """Base class for OpenAL objects."""
    @classmethod
    def _check_error(cls, message=None):
        """Check whether there is an OpenAL error and raise exception if present."""
        error_code = al.alGetError()
        if error_code != 0:
            error_string = al.alGetString(error_code)
            #TODO: Fix return type in generated code?
            error_string = ctypes.cast(error_string, ctypes.c_char_p)
            raise OpenALException(message=message,
                                  error_code=error_code,
                                  error_string=str(error_string.value))

    @classmethod
    def _raise_error(cls, message):
        """Raise an exception. Try to check for OpenAL error code too."""
        cls._check_error(message)
        raise OpenALException(message)


class OpenALDevice(OpenALObject):
    """OpenAL audio device."""
    def __init__(self, device_name=None):
        self._al_device = alc.alcOpenDevice(device_name)
        if self._al_device is None:
            raise OpenALException('No OpenAL devices.')

    def __del__(self):
        self.delete()

    def delete(self):
        if self._al_device is not None:
            alc.alcCloseDevice(self._al_device)
            self._al_device = None

    @property
    def is_ready(self):
        return self._al_device is not None

    def create_context(self):
        al_context = alc.alcCreateContext(self._al_device, None)
        return OpenALContext(self, al_context)

    def get_version(self):
        major = alc.ALCint()
        minor = alc.ALCint()
        alc.alcGetIntegerv(self._al_device, alc.ALC_MAJOR_VERSION,
                           ctypes.sizeof(major), major)
        alc.alcGetIntegerv(self._al_device, alc.ALC_MINOR_VERSION,
                           ctypes.sizeof(minor), minor)
        return major.value, minor.value

    def get_extensions(self):
        extensions = alc.alcGetString(self._al_device, alc.ALC_EXTENSIONS)
        if pyglet.compat_platform == 'darwin' or pyglet.compat_platform.startswith('linux'):
            return [str(x) for x in ctypes.cast(extensions, ctypes.c_char_p).value.split(' ')]
        else:
            return _split_nul_strings(extensions)


class OpenALContext(OpenALObject):
    def __init__(self, device, al_context):
        self.device = device
        self._al_context = al_context
        self.make_current()
        self.buffer_pool = OpenALBufferPool()

    def __del__(self):
        self.delete()

    def delete(self):
        if self._al_context is not None:
            # TODO: Check if this context is current
            alc.alcMakeContextCurrent(None)
            alc.alcDestroyContext(self._al_context)
            self._al_context = None

    def make_current(self):
        alc.alcMakeContextCurrent(self._al_context)

    def create_source(self):
        self.make_current()
        return OpenALSource(self)


class OpenALSource(OpenALObject):
    def __init__(self, context):
        self.context = context

        self._al_source = al.ALuint()
        al.alGenSources(1, self._al_source)
        self._check_error('Failed to create source.')

        self._state = al.ALint()
        self._get_state()

    def __del__(self):
        self.delete()

    def delete(self):
        if self._al_source is not None:
            al.alDeleteSources(1, self._al_source)
            self._check_error('Failed to delete source.')
            # TODO: delete buffers in use
            self._al_source = None

    @property
    def is_playing(self):
        self._get_state()
        return self._state.value == al.AL_PLAYING

    @property
    def buffers_processed(self):
        return self._get_int(al.AL_BUFFERS_PROCESSED)

    @property
    def byte_offset(self):
        return self._get_int(al.AL_BYTE_OFFSET)

    def play(self):
        al.alSourcePlay(self._al_source)
        self._check_error('Failed to play source.')

    def pause(self):
        al.alSourcePause(self._al_source)
        self._check_error('Failed to pause source.')

    def stop(self):
        al.alSourceStop(self._al_source)
        self._check_error('Filed to stop source.')

    def unqueue_buffers(self):
        processed = self.buffers_processed
        buffers = (al.ALuint * processed)()
        al.alSourceUnqueueBuffers(self._al_source, len(buffers), buffers)
        self._check_error('Failed to unqueue buffers from source.')
        for buf in buffers:
            self.buffer_pool.unqueue_buffer(buf)

    def _get_state(self):
        if self._al_source is not None:
            al.alGetSourcei(self._al_source, al.AL_SOURCE_STATE, self._state)
            self._check_error('Failed to get source state.')

    def _get_int(self, key):
        al_int = al.ALint()
        al.alGetSourcei(self._al_source, key, al_int)
        self._check_error('Failed to get value')
        return al_int.value


class OpenALBuffer(OpenALObject):
    @classmethod
    def create(cls):
        cls._check_error('Before allocating buffer.')
        al_buffer = al.ALuint()
        al.alGenBuffers(1, al_buffer)
        cls._check_error('Error allocating buffer.')
        return cls(al_buffer)

    def __init__(self, al_buffer):
        self._al_buffer = al_buffer
        assert self.is_valid

    def __del__(self):
        self.delete()

    @property
    def is_valid(self):
        self._check_error('Before validate buffer.')
        if self._al_buffer is None:
            return False
        valid = bool(al.alIsBuffer(self._al_buffer))
        if not valid:
            # Clear possible error due to invalid buffer
            al.alGetError()
        return valid

    @property
    def al_buffer(self):
        assert self.is_valid
        return self._al_buffer

    def delete(self):
        if self.is_valid:
            al.alDeleteBuffers(1, ctypes.byref(self._al_buffer))
            self._check_error('Error deleting buffer.')
            self._al_buffer = None


class OpenALBufferPool(object):
    """At least Mac OS X doesn't free buffers when a source is deleted; it just
    detaches them from the source.  So keep our own recycled queue.
    """
    def __init__(self):
        self._buffers = [] # list of free buffer names

    def __del__(self):
        self.clear()

    def __len__(self):
        return len(self._buffers)

    def clear(self):
        while self._buffers:
            self._buffers.pop().delete()

    def get_buffer(self):
        """Convenience for returning one buffer name"""
        return self.get_buffers(1)[0]

    def get_buffers(self, number):
        """Returns an array containing `number` buffer names.  The returned list must
        not be modified in any way, and may get changed by subsequent calls to
        get_buffers.
        """
        buffers = []
        while number > 0:
            if self._buffers:
                b = self._buffers.pop()
            else:
                b = OpenALBuffer.create()
            if b.is_valid:
                # Protect against implementations that DO free buffers
                # when they delete a source - carry on.
                buffers.append(b)
                number -= 1

        return buffers

    def unqueue_buffer(self, buf):
        """A buffer has finished playing, free it."""
        if buf.is_valid:
            self._buffers.append(buf)


from __future__ import division
from builtins import range
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

from pyglet.media.sources.base import Source, AudioFormat, AudioData

import ctypes
import os
import math
import struct


def future_round(value):
    """Function to have a round that functions the same on Py2 and Py3."""
    # TODO: Check if future can replace this (as of August 2016, it cannot).
    return int(round(value))


class ProceduralSource(Source):
    def __init__(self, duration, sample_rate=44800, sample_size=16):
        self._duration = float(duration)
        self.audio_format = AudioFormat(
            channels=1,
            sample_size=sample_size,
            sample_rate=sample_rate)

        self._offset = 0
        self._sample_rate = sample_rate
        self._sample_size = sample_size
        self._bytes_per_sample = sample_size >> 3
        self._bytes_per_second = self._bytes_per_sample * sample_rate
        self._max_offset = int(self._bytes_per_second * self._duration)
        
        if self._bytes_per_sample == 2:
            self._max_offset &= 0xfffffffe

    def get_audio_data(self, num_bytes):
        num_bytes = min(num_bytes, self._max_offset - self._offset)
        if num_bytes <= 0:
            return None
        
        timestamp = float(self._offset) / self._bytes_per_second
        duration = float(num_bytes) / self._bytes_per_second
        data = self._generate_data(num_bytes, self._offset)
        self._offset += num_bytes

        return AudioData(data, num_bytes, timestamp, duration, [])

    def _generate_data(self, num_bytes, offset):
        """Generate `num_bytes` bytes of data.

        Return data as ctypes array or string.
        """
        raise NotImplementedError('abstract')

    def seek(self, timestamp):
        self._offset = int(timestamp * self._bytes_per_second)

        # Bound within duration
        self._offset = min(max(self._offset, 0), self._max_offset)

        # Align to sample
        if self._bytes_per_sample == 2:
            self._offset &= 0xfffffffe

    def save(self, filename):
        """Save the audio to disk as a standard RIFF Wave.

        A standard RIFF wave header will be added to the raw PCM
        audio data when it is saved to disk.

        :Parameters:
            `filename` : str
                The file name to save as.

        """
        data = self._generate_data(self._max_offset, 0)
        header = struct.pack('<4sI8sIHHIIHH4sI',
                             b"RIFF",
                             len(data) + 44 - 8,
                             b"WAVEfmt ",
                             16,                # Default for PCM
                             1,                 # Default for PCM
                             1,                 # Number of channels
                             self._sample_rate,
                             self._bytes_per_second,
                             self._bytes_per_sample,
                             self._sample_size,
                             b"data",
                             len(data))

        with open(filename, "wb") as f:
            f.write(header)
            f.write(data)


class Silence(ProceduralSource):
    def _generate_data(self, num_bytes, offset):
        if self._bytes_per_sample == 1:
            return '\127' * num_bytes
        else:
            return '\0' * num_bytes


class WhiteNoise(ProceduralSource):
    def _generate_data(self, num_bytes, offset):
        return os.urandom(num_bytes)


class Sine(ProceduralSource):
    def __init__(self, duration, frequency=440, **kwargs):
        super(Sine, self).__init__(duration, **kwargs)
        self.frequency = frequency
        
    def _generate_data(self, num_bytes, offset):
        if self._bytes_per_sample == 1:
            start = offset
            samples = num_bytes
            bias = 127
            amplitude = 127
            data = (ctypes.c_ubyte * samples)()
        else:
            start = offset >> 1
            samples = num_bytes >> 1
            bias = 0
            amplitude = 32767
            data = (ctypes.c_short * samples)()
        step = self.frequency * (math.pi * 2) / self.audio_format.sample_rate
        for i in range(samples):
            data[i] = future_round(math.sin(step * (i + start)) * amplitude + bias)
        return data


class Saw(ProceduralSource):
    def __init__(self, duration, frequency=440, **kwargs):
        super(Saw, self).__init__(duration, **kwargs)
        self.frequency = frequency
        
    def _generate_data(self, num_bytes, offset):
        # XXX TODO consider offset
        if self._bytes_per_sample == 1:
            samples = num_bytes
            value = 127
            maximum = 255
            minimum = 0
            data = (ctypes.c_ubyte * samples)()
        else:
            samples = num_bytes >> 1
            value = 0
            maximum = 32767
            minimum = -32768
            data = (ctypes.c_short * samples)()
        step = (maximum - minimum) * 2 * self.frequency / self.audio_format.sample_rate
        for i in range(samples):
            value += step
            if value > maximum:
                value = maximum - (value - maximum)
                step = -step
            if value < minimum:
                value = minimum - (value - minimum)
                step = -step
            data[i] = future_round(value)
        return data


class Square(ProceduralSource):
    def __init__(self, duration, frequency=440, **kwargs):
        super(Square, self).__init__(duration, **kwargs)
        self.frequency = frequency

    def _generate_data(self, num_bytes, offset):
        # XXX TODO consider offset
        if self._bytes_per_sample == 1:
            samples = num_bytes
            value = 0
            amplitude = 255
            data = (ctypes.c_ubyte * samples)()
        else:
            samples = num_bytes >> 1
            value = -32768
            amplitude = 65535
            data = (ctypes.c_short * samples)()
        period = self.audio_format.sample_rate / self.frequency / 2
        count = 0
        for i in range(samples):
            count += 1
            if count >= period:
                value = amplitude - value
                count = 0
            data[i] = future_round(value)
        return data


class FM(ProceduralSource):
    def __init__(self, duration, carrier=440, modulator=440, mod_index=1, **kwargs):
        super(FM, self).__init__(duration, **kwargs)
        self.carrier = carrier
        self.modulator = modulator
        self.mod_index = mod_index

    def _generate_data(self, num_bytes, offset):
        if self._bytes_per_sample == 1:
            start = offset
            samples = num_bytes
            bias = 127
            amplitude = 127
            data = (ctypes.c_ubyte * samples)()
        else:
            start = offset >> 1
            samples = num_bytes >> 1
            bias = 0
            amplitude = 32767
            data = (ctypes.c_short * samples)()
        car_step = 2 * math.pi * self.carrier
        mod_step = 2 * math.pi * self.modulator
        mod_index = self.mod_index
        sample_rate = self._sample_rate
        # FM equation:  sin((2 * pi * carrier) + sin(2 * pi * modulator))
        for i in range(samples):
            increment = (i + start) / sample_rate
            data[i] = future_round(
                math.sin(car_step * increment +
                         mod_index * math.sin(mod_step * increment))
                * amplitude + bias)
        return data

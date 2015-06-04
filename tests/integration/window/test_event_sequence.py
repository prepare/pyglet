from builtins import object
import unittest
import time

from pyglet import window


class EventSequenceTest(object):
    """Base for testing event sequences on a window."""
    next_sequence = 0
    last_sequence = 0
    finished = False
    timeout = 2
    start_time = time.time()

    def check_sequence(self, sequence, name):
        if self.next_sequence == 0 and sequence != 0:
            return
        if sequence == 0:
            self.start_time = time.time()
        if not self.finished:
            if self.next_sequence != sequence:
                self.failed = 'ERROR: %s out of order' % name
            else:
                self.next_sequence += 1
        if self.next_sequence > self.last_sequence:
            self.finished = True

    def check(self):
        self.assertTrue(time.time() - self.start_time < self.timeout,
                        'Did not receive next expected event: %d' % self.last_sequence)
        failed = getattr(self, 'failed', None)
        if failed:
            self.fail(failed)


class WindowShowEventSequenceTest(EventSequenceTest, unittest.TestCase):
    """Event sequence when hidden window is set to visible."""
    last_sequence = 3

    def on_resize(self, width, height):
        self.check_sequence(1, 'on_resize')

    def on_show(self):
        self.check_sequence(2, 'on_show')

    def on_expose(self):
        self.check_sequence(3, 'on_expose')

    def test_method(self):
        win = window.Window(visible=False)
        try:
            win.dispatch_events()
            win.push_handlers(self)

            win.set_visible(True)
            self.check_sequence(0, 'begin')
            while not win.has_exit and not self.finished:
                win.dispatch_events()
                self.check()
        finally:
            win.close()


class WindowCreateEventSequenceTest(EventSequenceTest, unittest.TestCase):
    last_sequence = 3

    def on_resize(self, width, height):
        self.check_sequence(1, 'on_resize')

    def on_show(self):
        self.check_sequence(2, 'on_show')

    def on_expose(self):
        self.check_sequence(3, 'on_expose')

    def test_method(self):
        win = window.Window()
        try:
            win.push_handlers(self)
            self.check_sequence(0, 'begin')
            while not win.has_exit and not self.finished:
                win.dispatch_events()
                self.check()
        finally:
            win.close()


class WindowCreateFullScreenEventSequenceTest(EventSequenceTest, unittest.TestCase):
    last_sequence = 3

    def on_resize(self, width, height):
        self.check_sequence(1, 'on_resize')

    def on_show(self):
        self.check_sequence(2, 'on_show')

    def on_expose(self):
        self.check_sequence(3, 'on_expose')

    def test_method(self):
        win = window.Window(fullscreen=True)
        try:
            win.push_handlers(self)
            self.check_sequence(0, 'begin')
            while not win.has_exit and not self.finished:
                win.dispatch_events()
                self.check()
        finally:
            win.close()


class WindowSetFullScreenEventSequenceTest(EventSequenceTest, unittest.TestCase):
    last_sequence = 2

    def on_resize(self, width, height):
        self.check_sequence(1, 'on_resize')

    def on_expose(self):
        self.check_sequence(2, 'on_expose')

    def test_method(self):
        win = window.Window()
        try:
            win.dispatch_events()

            win.push_handlers(self)
            win.set_fullscreen()
            self.check_sequence(0, 'begin')
            while not win.has_exit and not self.finished:
                win.dispatch_events()
                self.check()
        finally:
            win.close()


class WindowUnsetFullScreenEventSequenceTest(EventSequenceTest, unittest.TestCase):
    last_sequence = 2

    def on_resize(self, width, height):
        self.check_sequence(1, 'on_resize')

    def on_expose(self):
        self.check_sequence(2, 'on_expose')

    def test_method(self):
        win = window.Window(fullscreen=True)
        try:
            win.dispatch_events()
            win.push_handlers(self)

            win.set_fullscreen(False)
            self.check_sequence(0, 'begin')
            while not win.has_exit and not self.finished:
                win.dispatch_events()
                self.check()
        finally:
            win.close()

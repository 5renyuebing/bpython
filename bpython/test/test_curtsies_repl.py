# coding: utf8
import code
from contextlib import contextmanager
from functools import partial
import os
from StringIO import StringIO
import sys
import tempfile

import unittest
try:
    from unittest import skip
except ImportError:
    def skip(f):
        return lambda self: None

py3 = (sys.version_info[0] == 3)

from bpython.curtsiesfrontend import repl as curtsiesrepl
from bpython.curtsiesfrontend import interpreter
from bpython import config
from bpython import args

def setup_config(conf):
    config_struct = config.Struct()
    config.loadini(config_struct, os.devnull)
    for key, value in conf.items():
        if not hasattr(config_struct, key):
            raise ValueError("%r is not a valid config attribute" % (key,))
        setattr(config_struct, key, value)
    return config_struct


class TestCurtsiesRepl(unittest.TestCase):

    def setUp(self):
        self.repl = create_repl()

    def cfwp(self, source):
        return interpreter.code_finished_will_parse(source, self.repl.interp.compile)

    def test_code_finished_will_parse(self):
        self.repl.buffer = ['1 + 1']
        self.assertTrue(self.cfwp('\n'.join(self.repl.buffer)), (True, True))
        self.repl.buffer = ['def foo(x):']
        self.assertTrue(self.cfwp('\n'.join(self.repl.buffer)), (False, True))
        self.repl.buffer = ['def foo(x)']
        self.assertTrue(self.cfwp('\n'.join(self.repl.buffer)), (True, False))
        self.repl.buffer = ['def foo(x):', 'return 1']
        self.assertTrue(self.cfwp('\n'.join(self.repl.buffer)), (True, False))
        self.repl.buffer = ['def foo(x):', '    return 1']
        self.assertTrue(self.cfwp('\n'.join(self.repl.buffer)), (True, True))
        self.repl.buffer = ['def foo(x):', '    return 1', '']
        self.assertTrue(self.cfwp('\n'.join(self.repl.buffer)), (True, True))

    def test_external_communication(self):
        self.assertEqual(type(self.repl.help_text()), type(b''))
        self.repl.send_current_block_to_external_editor()
        self.repl.send_session_to_external_editor()

    def test_external_communication_encoding(self):
        with captured_output():
            self.repl.display_lines.append(u'>>> "åß∂ƒ"')
            self.repl.send_session_to_external_editor()

    def test_get_last_word(self):
        self.repl.rl_history.entries=['1','2 3','4 5 6']
        self.repl._set_current_line('abcde')
        self.repl.get_last_word()
        self.assertEqual(self.repl.current_line,'abcde6')
        self.repl.get_last_word()
        self.assertEqual(self.repl.current_line,'abcde3')

    @skip # this is the behavior of bash - not currently implemented
    def test_get_last_word_with_prev_line(self):
        self.repl.rl_history.entries=['1','2 3','4 5 6']
        self.repl._set_current_line('abcde')
        self.repl.up_one_line()
        self.assertEqual(self.repl.current_line,'4 5 6')
        self.repl.get_last_word()
        self.assertEqual(self.repl.current_line,'4 5 63')
        self.repl.get_last_word()
        self.assertEqual(self.repl.current_line,'4 5 64')
        self.repl.up_one_line()
        self.assertEqual(self.repl.current_line,'2 3')

@contextmanager # from http://stackoverflow.com/a/17981937/398212 - thanks @rkennedy
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

def create_repl(**kwargs):
    config = setup_config({'editor':'true'})
    repl = curtsiesrepl.Repl(config=config, **kwargs)
    os.environ['PAGER'] = 'true'
    repl.width = 50
    repl.height = 20
    return repl

class TestFutureImports(unittest.TestCase):

    def test_repl(self):
        repl = create_repl()
        with captured_output() as (out, err):
            repl.push('from __future__ import division')
            repl.push('1 / 2')
        self.assertEqual(out.getvalue(), '0.5\n')

    def test_interactive(self):
        interp = code.InteractiveInterpreter(locals={})
        with captured_output() as (out, err):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as f:
                f.write('from __future__ import division\n')
                f.write('print(1/2)\n')
                f.flush()
                args.exec_code(interp, [f.name])

            repl = create_repl(interp=interp)
            repl.push('1 / 2')

        self.assertEqual(out.getvalue(), '0.5\n0.5\n')

class TestPredictedIndent(unittest.TestCase):
    def setUp(self):
        self.repl = create_repl()

    def test_simple(self):
        self.assertEqual(self.repl.predicted_indent(''), 0)
        self.assertEqual(self.repl.predicted_indent('class Foo:'), 4)
        self.assertEqual(self.repl.predicted_indent('class Foo: pass'), 0)
        self.assertEqual(self.repl.predicted_indent('def asdf():'), 4)
        self.assertEqual(self.repl.predicted_indent('def asdf(): return 7'), 0)

    @skip
    def test_complex(self):
        self.assertEqual(self.repl.predicted_indent('[a,'), 1)
        self.assertEqual(self.repl.predicted_indent('reduce(asdfasdf,'), 7)


if __name__ == '__main__':
    unittest.main()

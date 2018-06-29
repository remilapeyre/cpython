import io
import os
import sys
import textwrap
import unittest
import types
from subprocess import Popen, PIPE
from test import support
from test.support.script_helper import assert_python_ok, assert_python_failure
from unittest import mock


class TestTool(unittest.TestCase):
    data = """

        [["blorpie"],[ "whoops" ] , [
                                 ],\t"d-shtaeou",\r"d-nthiouh",
        "i-vhbjkhnth", {"nifty":87}, {"morefield" :\tfalse,"field"
            :"yes"}  ]
           """

    expect_without_sort_keys = textwrap.dedent("""\
    [
        [
            "blorpie"
        ],
        [
            "whoops"
        ],
        [],
        "d-shtaeou",
        "d-nthiouh",
        "i-vhbjkhnth",
        {
            "nifty": 87
        },
        {
            "field": "yes",
            "morefield": false
        }
    ]
    """)

    expect = textwrap.dedent("""\
    [
        [
            "blorpie"
        ],
        [
            "whoops"
        ],
        [],
        "d-shtaeou",
        "d-nthiouh",
        "i-vhbjkhnth",
        {
            "nifty": 87
        },
        {
            "morefield": false,
            "field": "yes"
        }
    ]
    """)

    def test_stdin_stdout(self):
        args = sys.executable, '-m', 'json.tool'
        with Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE) as proc:
            out, err = proc.communicate(self.data.encode())
        self.assertEqual(out.splitlines(), self.expect.encode().splitlines())
        self.assertEqual(err, b'')

    def _create_infile(self):
        infile = support.TESTFN
        with open(infile, "w") as fp:
            self.addCleanup(os.remove, infile)
            fp.write(self.data)
        return infile

    def test_infile_stdout(self):
        infile = self._create_infile()
        rc, out, err = assert_python_ok('-m', 'json.tool', infile)
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines(), self.expect.encode().splitlines())
        self.assertEqual(err, b'')

    def test_infile_outfile(self):
        infile = self._create_infile()
        outfile = support.TESTFN + '.out'
        rc, out, err = assert_python_ok('-m', 'json.tool', infile, outfile)
        self.addCleanup(os.remove, outfile)
        with open(outfile, "r") as fp:
            self.assertEqual(fp.read(), self.expect)
        self.assertEqual(rc, 0)
        self.assertEqual(out, b'')
        self.assertEqual(err, b'')

    def test_infile_same_outfile(self):
        infile = self._create_infile()
        rc, out, err = assert_python_ok('-m', 'json.tool', infile, infile)
        self.assertEqual(rc, 0)
        self.assertEqual(out, b'')
        self.assertEqual(err, b'')

    def test_unavailable_outfile(self):
        infile = self._create_infile()
        rc, out, err = assert_python_failure('-m', 'json.tool', infile, '/bla/outfile')
        self.assertEqual(rc, 2)
        self.assertEqual(out, b'')
        err = err.decode().splitlines()
        self.assertEqual(err[0], 'usage: python -m json.tool [-h] [--sort-keys] [infile] [outfile]')
        self.assertEqual(err[1], "python -m json.tool: error: can't open '/bla/outfile': [Errno 2] No such file or directory: '/bla/outfile'")

    def test_help_flag(self):
        rc, out, err = assert_python_ok('-m', 'json.tool', '-h')
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith(b'usage: '))
        self.assertEqual(err, b'')

    def test_sort_keys_flag(self):
        infile = self._create_infile()
        rc, out, err = assert_python_ok('-m', 'json.tool', '--sort-keys', infile)
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines(),
                         self.expect_without_sort_keys.encode().splitlines())
        self.assertEqual(err, b'')

    def test_no_fd_leak_infile_outfile(self):
        closed = []
        opened = []
        io_open = io.open

        def open(*args, **kwargs):
            fd = io_open(*args, **kwargs)
            opened.append(fd)
            fd_close = fd.close
            def close(self):
                closed.append(self)
                fd_close()
            fd.close = types.MethodType(close, fd)
            return fd

        infile = self._create_infile()
        with mock.patch('builtins.open', side_effect=open):
            with mock.patch.object(sys, 'argv', ['tool.py', infile, infile + '.out']):
                import json.tool
                json.tool.main()

        os.unlink(infile + '.out')
        self.assertEqual(opened, closed)
        self.assertEqual(len(opened), len(closed))

    def test_no_fd_leak_same_infile_outfile(self):
        closed = []
        opened = []
        io_open = io.open

        def open(*args, **kwargs):
            fd = io_open(*args, **kwargs)
            opened.append(fd)
            fd_close = fd.close
            def close(self):
                closed.append(self)
                fd_close()
            fd.close = types.MethodType(close, fd)
            return fd

        infile = self._create_infile()
        with mock.patch('builtins.open', side_effect=open):
            with mock.patch.object(sys, 'argv', ['tool.py', infile, infile]):
                try:
                    import json.tool
                    json.tool.main()
                except SystemExit:  # We expect SystemExit to happen on c9d43c
                    pass

        self.assertEqual(opened, closed)
        self.assertEqual(len(opened), len(closed))

import os
import sys
import unittest
import shlex
import imputil
import glob
import logging
import warnings

from pykickstart.version import versionMap, returnClassForVersion
from pykickstart.errors import *
from rhpl.translate import _

logger = logging.getLogger()
logger.setLevel(logging.INFO)

plainformatter = logging.Formatter("%(message)s")
console_stdout = logging.StreamHandler(sys.stdout)
console_stdout.setFormatter(plainformatter)
logger.addHandler(console_stdout)

# Base class for any test case
class CommandTest(unittest.TestCase):
    def setUp(self):
        '''Perform any command setup'''
        unittest.TestCase.setUp(self)
        self.handler = None

        # ignore DeprecationWarning
        warnings.simplefilter("ignore", category=DeprecationWarning, append=0)

    def tearDown(self):
        '''Undo anything performed by setUp(self)'''
        # reset warnings
        warnings.filters = warnings.filters[1:]

        unittest.TestCase.tearDown(self)

    def getParser(self, cmd):
        '''Find a handler using the class name.  Return the requested command
        object.'''
        if self.handler is None:
            version = self.__class__.__name__.split("_")[0]
            self.handler = returnClassForVersion(version)
        return self.handler().commands[cmd]

    def assert_parse(self, inputStr, expectedStr=None):
        '''KickstartParseError is not raised and the resulting string matches
        supplied value'''
        args = shlex.split(inputStr)
        parser = self.getParser(args[0])

        if expectedStr is not None:
            result = parser.parse(args[1:])
            self.assertEqual(str(result), expectedStr)
        else:
            self.assertNotRaises(KickstartParseError, parser.parse, args[1:])

    def assert_parse_error(self, inputStr, exception=KickstartParseError):
        '''Assert that parsing the supplied string raises a
        KickstartParseError'''
        args = shlex.split(inputStr)
        parser = self.getParser(args[0])
        self.assertRaises(exception, parser.parse, args[1:])

    def assert_deprecated(self, cmd, opt):
        '''Ensure that the provided option is listed as deprecated'''
        parser = self.getParser(cmd)

        for op in parser.op.option_list:
            if op.dest == opt:
                self.assert_(op.deprecated)

    def assert_removed(self, cmd, opt):
        '''Ensure that the provided option is not present in option_list'''
        parser = self.getParser(cmd)
        for op in parser.op.option_list:
            self.assertNotEqual(op.dest, opt)

    def assert_required(self, cmd, opt):
        '''Ensure that the provided option is labelled as required in
        option_list'''
        parser = self.getParser(cmd)
        for op in parser.op.option_list:
            if op.dest == opt:
                self.assert_(op.required)

    def assert_type(self, cmd, opt, opt_type):
        '''Ensure that the provided option is of the requested type'''
        parser = self.getParser(cmd)
        for op in parser.op.option_list:
            if op.dest == opt:
                self.assertEqual(op.type, opt_type)

def loadTests(moduleDir):
    '''taken from firstboot/loader.py'''

    tstList = list()

    # Make sure moduleDir is in the system path so imputil works.
    if not moduleDir in sys.path:
        sys.path.append(moduleDir)

    # Get a list of all *.py files in moduleDir
    moduleList = []
    lst = map(lambda x: os.path.splitext(os.path.basename(x))[0],
              glob.glob(moduleDir + "/*.py"))

    # Inspect each .py file found
    for module in lst:
        if module == "__init__":
            continue

        logging.debug(_("Loading module %s") % module)

        # Attempt to load the found module.
        try:
            found = imputil.imp.find_module(module)
            loaded = imputil.imp.load_module(module, found[0], found[1], found[2])
        except ImportError, e:
            logging.exception(_("Error loading module %s.") % module)

        # Find class names that match "_TestCase"
        beforeCount = len(tstList)
        for obj in loaded.__dict__.keys():
            if obj.endswith("_TestCase"):
                tstList.append(loaded.__dict__[obj])
        afterCount = len(tstList)

        # Warn if no tests found
        if beforeCount == afterCount:
            logging.warning(_("Module %s does not contain any test cases; skipping.") % module)
            continue

    return tstList

# Run the tests
if __name__ == "__main__":

    # Create a test suite
    PyKickstartTestSuite = unittest.TestSuite()

    # Add tests for all commands supplied
    tstList = loadTests(os.path.join(os.environ.get("PWD"), "tests/commands"))
    for tst in tstList:
        PyKickstartTestSuite.addTest(tst())

    # Run tests
    unittest.main(defaultTest="PyKickstartTestSuite")
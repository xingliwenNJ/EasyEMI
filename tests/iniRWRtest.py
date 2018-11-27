import sys
sys.path.append('../')

from easyemi.gui import initialize
from pathlib import Path
import os
import random
import unittest

class initVariablesTestCase(unittest.TestCase):
    def setUp(self):
        self.testfile = Path(os.path.dirname(os.path.abspath(__file__)) / 'test.ini')
        self.config = initialize.iniConfig(self.testfile)
        self.generate_config_file()

    def generate_config_file(self):
        #Randomize variables to write to test.ini
        self.np = random.randint(0, 100)
        self.t = random.randint(0, 30000)
        self.wp = self.testfile

        num_list = []
        for i in range(4):
            num_list.append(random.randint(0, 255))
        self.ip = '.'.join(str(e) for e in num_list)
        self.gpib = random.randint(1, 100)

        choice = random.randint(0, 1)
        if choice:
            self.var = 'TCPIP::' + str(self.ip) + '::INSTR'
        else:
            self.var = 'GPIB::' + str(self.gpib) + '::INSTR'
        
        self.config.save_config(self.np, self.t, self.wp, 
                self.ip, self.gpib, self.var)

    def test_write(self):
        self.assertTrue(self.testfile.is_file())

    def test_vars(self):
        self.config.read_config()
        self.assertEqual(self.np, int(self.config.numpeaks))
        self.assertEqual(self.t, int(self.config.timer))
        self.assertEqual(str(self.wp), self.config.workspace)
        self.assertEqual(self.ip, self.config.resourceip)
        self.assertEqual(self.gpib, int(self.config.resourcegpib))
        self.assertEqual(self.var, self.config.resourcevar)

    def tearDown(self):
        os.remove(self.testfile)

if __name__ == '__main__':
    unittest.main()

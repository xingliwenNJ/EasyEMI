'''
The persistentVariables class holds initialization
variables in a base.ini file

[DEFAULT]
numpeaks = number of peaks to store in peak table
timer = time for scan to complete
workspace = directory to store files

[RESOURCE]
resourceip = ip address of instrument
resourcevar = full SCPI resource string
'''
import configparser
import os
from pathlib import Path

fp = Path(os.path.dirname(os.path.abspath(__file__)))

class iniConfig:
    def __init__(self, ini_file):
        self.ini_file = ini_file
        self.config = configparser.ConfigParser()
    
    def read_config(self):
        # Set variables from base.ini
        self.config.read(self.ini_file)
        self.numpeaks = self.config['DEFAULT']['numpeaks']
        self.timer = self.config['DEFAULT']['timer']
        self.workspace = self.config['DEFAULT']['workspace']

        self.resourceip = self.config['RESOURCE']['resourceip']
        self.resourcegpib = self.config['RESOURCE']['resourcegpib']
        self.resourcevar = self.config['RESOURCE']['resourcevar']

    def save_config(self, np = 6, t = 15, wp = fp, 
            ip = '192.168.1.1', gpib = 20, 
            var = 'TCPIP::192.168.1.2::INSTR'):
        # Pass variables to be changed and saved in base.ini

        self.config['DEFAULT'] = {'numpeaks': np,
                                  'timer': t,
                                  'workspace': wp}
        
        self.config['RESOURCE'] = {'resourceip': ip,
                                   'resourcegpib': gpib,
                                   'resourcevar': var}

        with open(self.ini_file, 'w') as configfile:
            self.config.write(configfile)


if __name__ == '__main__':
    test = iniConfig(fp / 'base.ini')
    test.read_config()

    print('# of peaks:', test.numpeaks)
    print('Scan time:', test.timer)
    print('Working Directory:', test.workspace)
    print('Instrument IP:', test.resourceip)
    print('Instrument GPIB:', test.resourcegpib)
    print('SCPI Resource:', test.resourcevar)

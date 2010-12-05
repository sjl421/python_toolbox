import os
import shutil
import tempfile

from garlicsim.general_misc.temp_value_setters import \
    TempWorkingDirectorySetter
from garlicsim.general_misc import sys_tools

import garlicsim.scripts.start_simpack
start_simpack_file = garlicsim.scripts.start_simpack.__file__




def test():
    # tododoc: do this. Don't forget to test the simpack works.
    temp_dir = tempfile.mkdtemp(prefix='temp_garlicsim_')
    try:
        with TempWorkingDirectorySetter(temp_dir):
            output = sys_tools.execute('%s my_simpack' % start_simpack_file)
            assert output == ("`my_simpack` created successfully! Explore the"
                              "`my_simpack` folder and start filling in the "
                              "contents of your new simpack." % (name, name))
            
            
    finally:
        shutil.rmtree(temp_dir)

        
def test_implicit_help():
    pass#tododoc
        

def test_explicit_help():
    pass#tododoc
    
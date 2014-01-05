# Copyright 2009-2014 Ram Rachum.
# This program is distributed under the MIT license.

import pathlib

import python_toolbox
from python_toolbox import temp_file_tools

from python_toolbox import file_tools


def test():
    with temp_file_tools.TemporaryFolder(prefix='test_python_toolbox_') as \
                                                              temporary_folder:
        get_file_names_set = \
                  lambda: set(path.name for path in temporary_folder.glob('*'))
        assert not get_file_names_set()
        
        file_path = temporary_folder / 'meow.txt'
        string_to_write = "I'm a cat, hear me meow!"
        
        assert file_tools.write_to_file_renaming_if_taken(
                          file_path, string_to_write) == len(string_to_write)
        
        with file_path.open('r') as file:
            assert file.read() == string_to_write
            
        assert get_file_names_set() == {'meow.txt'}
            
        
        assert file_tools.write_to_file_renaming_if_taken(
                          file_path, string_to_write) == len(string_to_write)
        assert file_tools.write_to_file_renaming_if_taken(
                          file_path, string_to_write) == len(string_to_write)
        assert file_tools.write_to_file_renaming_if_taken(
                          file_path, string_to_write) == len(string_to_write)
            
        with (temporary_folder / 'meow (2).txt').open('r') as last_file_input:
            assert last_file_input.read() == string_to_write
        
        assert get_file_names_set() == {'meow.txt', 'meow (1).txt',
                                        'meow (2).txt', 'meow (3).txt'}
        
        with file_tools.create_file_renaming_if_taken(file_path) as last_file:
            assert not last_file.closed
            last_file.write(string_to_write[:5])
            last_file.write(string_to_write[5:])
            
        assert last_file.closed
        
        assert get_file_names_set() == {'meow.txt', 'meow (1).txt',
                                        'meow (2).txt', 'meow (3).txt',
                                        'meow (4).txt'}
        
        with pathlib.Path(last_file.name).open('r') as last_file_input:
            assert last_file_input.read() == string_to_write
            

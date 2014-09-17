# Copyright 2009-2014 Ram Rachum.
# This program is distributed under the MIT license.

from python_toolbox import cute_testing
from python_toolbox import sequence_tools

from python_toolbox.sequence_tools import CuteRange

infinity = float('inf')


def test_built_in():
    built_in_range_arguments_tuples = (
        (10,), (3,), (20, 30), (20, 30, 2), (20, 30, -2)
    )
    
    for built_in_range_arguments_tuple in built_in_range_arguments_tuples:
        cr0 = CuteRange(*built_in_range_arguments_tuple)
        assert type(cr0) == range
        assert isinstance(cr0, range)
        assert isinstance(cr0, CuteRange)
        cr1 = CuteRange(*built_in_range_arguments_tuple, _avoid_built_in_range=True)
        assert cr1.length == len(cr1)
        assert type(cr1) == CuteRange
        assert not isinstance(cr1, range)
        assert isinstance(cr1, CuteRange)
        assert tuple(cr0) == tuple(cr1)
        if cr0:
            assert cr0[0] == cr1[0]
            assert cr0[-1] == cr1[-1]
        assert repr(cr0)[1:] == repr(cr1)[5:]
        
def test_infinite():
    infinite_range_arguments_tuples = (
        (), (10, infinity), (10, infinity, 2), (100, -infinity, -7)
    )
    
    for infinite_range_arguments_tuple in infinite_range_arguments_tuples:
        cr0 = CuteRange(*infinite_range_arguments_tuple)
        assert type(cr0) == CuteRange
        assert not isinstance(cr0, range)
        assert isinstance(cr0, CuteRange)
        assert cr0.length == infinity and len(cr0) == 0
        assert isinstance(cr0[0], int)
        assert cr0[10:].length == cr0[200:].length == infinity
        assert sequence_tools.get_length(cr0[:10]) != infinity != \
                                           sequence_tools.get_length(cr0[:200])
        
def test_illegal():
    illegal_range_arguments_tuples = (
        (infinity, 10, -7), 
    )
    
    for illegal_range_arguments_tuple in illegal_range_arguments_tuples:
        with cute_testing.RaiseAssertor(TypeError):
            CuteRange(*illegal_range_arguments_tuple)
    
        
def test_float():
    cr = CuteRange(10, 20, 1.5)
    assert list(cr) == [10, 11.5, 13, 14.5, 16, 17.5, 19]
    assert len(cr) == len(list(cr)) == 7
    assert list(map(range(7), cr.__getitem__)) == list(cr)
    
    float_range_arguments_tuples = (
        (10, 20, 1.5), (20, 10.5, -0.33), (10.3, infinity, 2.5),
        (100, -infinity, -7.1), (10.5, 20)
    )
    
    for float_range_arguments_tuple in float_range_arguments_tuples:
        cr0 = CuteRange(*float_range_arguments_tuple)
        assert type(cr0) == CuteRange
        assert not isinstance(cr0, range)
        assert isinstance(cr0, CuteRange)
        assert float in list(map(type, cr0[:2]))
        
        
    
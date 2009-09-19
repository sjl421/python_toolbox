# Copyright 2009 Ram Rachum.
# This program is distributed under the LGPL2.1 license.

"""
todo: need to lock library to avoid thread trouble?

todo: need to raise an exception if we're getting pickled with
an old protocol?
"""

import uuid
import weakref

library = weakref.WeakValueDictionary()
 
class PersistentReadOnlyObject(object):
    
    def __new__(cls, *args):        
        assert len(args) in [0, 1]
        
        received_uuid = args[0] if args else None
        
        if received_uuid:
            # This section is for when we are called at unpickling time
            thing = library.pop(received_uuid, None)
            if thing:
                thing._PersistentReadOnlyObject__skip_setstate = True
                return thing
            else: # This object does not exist in our library yet; Let's add it
                thing = super(PersistentReadOnlyObject, cls).__new__(cls)
                thing._PersistentReadOnlyObject__uuid = received_uuid
                library[received_uuid] = thing
                return thing
                
        else:
            # This section is for when we are called at normal creation time
            thing = super(PersistentReadOnlyObject, cls).__new__(cls)
            new_uuid = uuid.uuid4()
            thing._PersistentReadOnlyObject__uuid = new_uuid
            library[new_uuid] = thing
            return thing
        
    def __getstate__(self):
        my_dict = dict(self.__dict__)
        del my_dict["_PersistentReadOnlyObject__uuid"]
        return my_dict
    
    def __getnewargs__(self):
        return (self._PersistentReadOnlyObject__uuid,)
    
    def __setstate__(self, state):
        if self.__dict__.pop("_PersistentReadOnlyObject__skip_setstate", None):
            return
        else:
            self.__dict__.update(state)
    
    def __deepcopy__(self, memo):
        return self
    
    def __copy__(self):
        return self


    
# --------------------------------------------------------------
"""
From here on it's just testing stuff; will be moved to another file.
"""
    
    
def play_around(queue, thing):
    import copy
    queue.put((thing, copy.deepcopy(thing),))

class Booboo(PersistentReadOnlyObject):
    def __init__(self):
        self.number = random.random()
    
if __name__ == "__main__":
    
    import multiprocessing
    import random
    import copy
    
    def same(a, b):
        return (a is b) and (a == b) and (id(a) == id(b)) and \
               (a.number == b.number)
    
    a = Booboo()
    b = copy.copy(a)
    c = copy.deepcopy(a)
    assert same(a, b) and same(b, c)
    
    my_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target = play_around,
                                      args=(my_queue, a,))
    process.start()
    process.join()
    things = my_queue.get()
    for thing in things:
        assert same(thing, a) and same(thing, b) and same(thing, c)
    print("all cool!")

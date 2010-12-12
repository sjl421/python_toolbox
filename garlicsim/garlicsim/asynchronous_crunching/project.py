# Copyright 2009-2010 Ram Rachum.
# This program is distributed under the LGPL2.1 license.

'''
This module defines the Project class.

See its documentation for more information.
'''

from __future__ import with_statement

from garlicsim.general_misc import cute_iter_tools
import garlicsim.general_misc.read_write_lock
from garlicsim.general_misc.infinity import Infinity
import garlicsim.general_misc.third_party.decorator
from garlicsim.general_misc import misc_tools
from garlicsim.general_misc import address_tools

import garlicsim.data_structures
import garlicsim.misc.simpack_grokker
import garlicsim.misc.step_profile

from crunching_manager import CrunchingManager
from job import Job
from crunching_profile import CrunchingProfile

__all__ = ["Project"]

@garlicsim.general_misc.third_party.decorator.decorator
def with_tree_lock(method, *args, **kwargs):
    '''
    A decorator used in Project's methods to use the tree lock (in write mode)
    as a context manager when calling the method.
    '''
    self = args[0]
    with self.tree.lock.write:
        return method(*args, **kwargs)


class Project(object):
    '''
    A simulation project. This is the flagship class of `garlicsim`.
    
    You create a project when you want to do a simulation which will crunch
    in the background with worker threads or worker processes.

    A project contains within it a tree.
        
    The crunching is taken care of by the CrunchingManager which is a part of
    every project. The CrunchingManager employs ThreadCrunchers and/or
    ProcessCrunchers to get the work done. To make the CrunchingManager take
    work from the crunchers and coordinate them, call the sync_crunchers method
    of the project.
    
    The crunching manager contains a list of jobs as an attribute `.jobs`. See
    documentation for garlicsim.asynchronous_crunching.Job for more info about
    jobs. The crunching manager will employ crunchers in order to complete the
    jobs. It will then take work from these crunchers, put it into the tree,
    and delete the jobs when they are completed.
    '''

    def __init__(self, simpack):
        
        if isinstance(simpack, garlicsim.misc.SimpackGrokker):
            self.simpack_grokker = simpack            
            self.simpack = self.simpack_grokker.simpack
        else: # The simpack we got is an actual simpack
            self.simpack = simpack
            self.simpack_grokker = garlicsim.misc.SimpackGrokker(simpack)

        self.tree = garlicsim.data_structures.Tree()
        
        self.crunching_manager = CrunchingManager(self)
        
        self.default_step_function = self.simpack_grokker.default_step_function
    

    def create_root(self, *args, **kwargs):
        '''
        Create a parentless node whose state is a simple plain state.
        
        The simulation package has to define the method `State.create_root` for
        this to work.
        
        Returns the node.
        '''
        state = self.simpack.State.create_root(*args, **kwargs)
        return self.root_this_state(state)

    
    def create_messy_root(self, *args, **kwargs):
        '''
        Creates a parentless node whose state is a random and messy state.
        
        The simulation package has to define the method
        `State.create_messy_root` for this to work.
        
        Returns the node.
        '''
        state = self.simpack.State.create_messy_root(*args, **kwargs)
        return self.root_this_state(state)

    
    def root_this_state(self, state):
        '''
        Take a state, wrap it in a node and add to the tree without a parent.
        
        Returns the node.
        '''
        return self.tree.add_state(state)

    
    def ensure_buffer(self, node, clock_buffer=0):
        '''
        Ensure there's a large enough buffer of nodes after `node`.

        This method will ensure that every path that starts at `node` will have
        a clock buffer of at least `clock_buffer` after `node`. If there isn't,
        the leaves of `node` will be crunched until there's a buffer of
        `clock_buffer` between `node` and each of the leaves.
        '''
        leaves_dict = node.get_all_leaves(max_clock_distance=clock_buffer)
        new_clock_target = node.state.clock + clock_buffer
        
        for leaf in leaves_dict.copy():
            if leaf.ends: # todo: Not every end should count.
                del leaves_dict[leaf]
        
        for item in leaves_dict.items():

            leaf = item[0]
            
            jobs_of_leaf = self.crunching_manager.get_jobs_by_node(leaf)
            
            if not jobs_of_leaf:
                step_profile = leaf.step_profile or \
                    self.build_step_profile()
                crunching_profile = CrunchingProfile(new_clock_target,
                                                     step_profile)
                job = Job(leaf, crunching_profile)
                self.crunching_manager.jobs.append(job)
                continue
            
            for job in jobs_of_leaf:
                job.crunching_profile.raise_clock_target(new_clock_target)
            
    
    def ensure_buffer_on_path(self, node, path, clock_buffer=0):
        '''
        Ensure there's a large enough buffer of nodes after `node` on `path`.

        This method will ensure that on the given path there will be a clock
        buffer of at least `clock_buffer` after `node`. If there isn't, the
        leaf at the end of the path will be crunched until the buffer is big
        enough.
        '''
        
        leaf = path.get_last_node(head=node)
        if leaf.ends: # todo: Not every end should count, I think.
            return
        
        new_clock_target = node.state.clock + clock_buffer     

        jobs_of_leaf = self.crunching_manager.get_jobs_by_node(leaf)
        
        if jobs_of_leaf:
            job = jobs_of_leaf[-1]
            # We only want to take one job. We're guessing the last, and 
            # therefore the most recent one, will be the most wanted by the
            # user.
            job.crunching_profile.raise_clock_target(new_clock_target)
            return job
        else:
            step_profile = leaf.step_profile or self.build_step_profile()
            crunching_profile = CrunchingProfile(new_clock_target,
                                                 step_profile)
            job = Job(leaf, crunching_profile)
            self.crunching_manager.jobs.append(job)
            return job

        
    def fork_to_edit(self, template_node):
        '''
        "Duplicate" the node, marking the new one as touched.
        
        The new node will have the same parent as `template_node`. The state of
        the new node is usually modified by the user after it is created, and
        after that the node is finalized and used in simulation.
        
        This is useful when you want to make some changes in the world state and
        see what they will cause in the simulation.
        
        Returns the node.
        '''
        return self.tree.fork_to_edit(template_node)

    
    def begin_crunching(self, node, clock_buffer=None, *args, **kwargs):
        '''
        Start a new crunching job from `node`, possibly forking the simulation.
        
        On the next call to .sync_crunchers, a cruncher will start working on
        the new job.
        
        If there are already jobs on that node, they will all be crunched
        independently of each other to create different forks.
        
        Any *args or **kwargs will be packed in a StepProfile object and passed to
        the step function. You may pass a StepProfile yourself, as the only
        argument, and it will be noticed and used.
        
        Returns the job.
        '''
        
        step_profile = self.build_step_profile(*args, **kwargs)
        
        clock_target = node.state.clock + clock_buffer
        
        crunching_profile = CrunchingProfile(clock_target, step_profile)
        
        job = Job(node, crunching_profile)
        
        self.crunching_manager.jobs.append(job)
        
        return job
    

    def sync_crunchers(self):
        '''
        Take work from the crunchers, and give them new instructions if needed.
        
        Talks with all the crunchers, takes work from them for implementing
        into the tree, retiring crunchers or recruiting new crunchers as
        necessary.

        Returns the total amount of nodes that were added to the tree in the
        process.
        '''        
        return self.crunching_manager.sync_crunchers()
    
    
    @with_tree_lock
    def simulate(self, node, iterations=1, *args, **kwargs):
        '''
        Simulate from the given node for the given number of iterations.
        
        The results are implemented the results into the tree. Note that the
        crunching for this is done synchronously, i.e. in the currrent thread.
        
        If you wish, in *args and **kwargs you may specify simulation parameters
        and/or a specific step function to use. (You may specify a step function
        either as the first positional argument or the `step_function` keyword
        argument.) You may also pass in an existing step profile as first
        argument.
        
        Returns the final node.
        '''
        # todo: is simulate a good name? Need to say it's synchronously
        
        step_profile = self.build_step_profile(*args, **kwargs)
        
        if self.simpack_grokker.history_dependent:
            return self.__history_dependent_simulate(node, iterations,
                                                     step_profile)
        else:
            return self.__non_history_dependent_simulate(node, iterations,
                                                         step_profile)
        
        
    @with_tree_lock        
    def __history_dependent_simulate(self, node, iterations,
                                     step_profile=None):
        '''
        Simulate from the given node for the given number of iterations.
        
        (Internal function for history-dependent simulations only.)
        
        The results are implemented the results into the tree. Note that the
        crunching for this is done synchronously, i.e. in the currrent thread.
        
        A step profile may be passed to be used with the step function.
        
        Returns the final node.
        '''
        
        if step_profile is None:
            step_profile = self.build_step_profile()
        
        path = node.make_containing_path()
        history_browser = \
            garlicsim.synchronous_crunching.HistoryBrowser(path, tail_node=node)
        
        iterator = self.simpack_grokker.get_step_iterator(history_browser,
                                                          step_profile)
        finite_iterator = cute_iter_tools.shorten(iterator, iterations)
        
        current_node = node
        first_run = True
        try:
            for current_state in finite_iterator:
                current_node = self.tree.add_state(current_state,
                                                   parent=current_node,
                                                   step_profile=step_profile)
                history_browser.tail_node = current_node
                if first_run:
                    history_browser.path = current_node.make_containing_path()
                    # Just once, after the first run, we set the path of the
                    # history browser to be the new tail_node's path. Why?
                    
                    # Because just after the first run we've created the first
                    # new node, possibly causing a fork. Because of the new
                    # fork, the original path that we created at the beginning
                    # of this method will get confused and take the old timeline
                    # instead of the new timeline. (And it wouldn't even have
                    # the tail_node to stop it, because that would be on the new
                    # timeline.) So we create a new path for the history
                    # browser. We only need to do this once, because after the
                    # first node we work on one straight timeline and we don't
                    # fork the tree any more.
        
        except garlicsim.misc.WorldEnded:
            self.tree.make_end(current_node, step_profile)
            
        return current_node
    
    
    @with_tree_lock
    def __non_history_dependent_simulate(self, node, iterations,
                                         step_profile=None):
        '''
        Simulate from the given node for the given number of iterations.
        
        (Internal function for non-history-dependent simulations only.)
        
        The results are implemented the results into the tree. Note that the
        crunching for this is done synchronously, i.e. in the currrent thread.
        
        A step profile may be passed to be used with the step function.
        
        Returns the final node.
        '''
        
        if step_profile is None:
            step_profile = self.build_step_profile()

        state = node.state
                
        iterator = self.simpack_grokker.get_step_iterator(state, step_profile)
        finite_iterator = cute_iter_tools.shorten(iterator, iterations)
        
        current_node = node
        
        try:
            for current_state in finite_iterator:
                current_node = self.tree.add_state(current_state,
                                                   parent=current_node,
                                                   step_profile=step_profile)
        except garlicsim.misc.WorldEnded:
            self.tree.make_end(current_node, step_profile)
            
        return current_node
    
    
    def iter_simulate(self, node, iterations=1, *args, **kwargs):
        '''
        Simulate from the given node for the given number of iterations.
        
        The results are implemented into the tree. Note that the crunching for
        this is done synchronously, i.e. in the currrent thread.
        
        This returns a generator that yields all the nodes one-by-one, from the
        initial node to the final one.
            
        If you wish, in *args and **kwargs you may specify simulation parameters
        and/or a specific step function to use. (You may specify a step function
        either as the first positional argument or the `step_function` keyword
        argument.) You may also pass in an existing step profile as first
        argument.
        '''
        
        step_profile = self.build_step_profile(*args, **kwargs)
        
        if self.simpack_grokker.history_dependent:
            return self.__history_dependent_iter_simulate(node, iterations,
                                                          step_profile)
        else:
            return self.__non_history_dependent_iter_simulate(node, iterations,
                                                              step_profile)
        
                
    def __history_dependent_iter_simulate(self, node, iterations,
                                          step_profile=None):
        '''
        Simulate from the given node for the given number of iterations.
        
        (Internal function for history-dependent simulations only.)
        
        The results are implemented into the tree. Note that the crunching for
        this is done synchronously, i.e. in the currrent thread.
        
        This returns a generator that yields all the nodes one-by-one, from the
        initial node to the final one.
        
        A step profile may be passed to be used with the step function.
        '''
        
        if step_profile is None:
            step_profile = self.build_step_profile()
        
        path = node.make_containing_path()
        history_browser = \
            garlicsim.synchronous_crunching.HistoryBrowser(path, tail_node=node)
        
        iterator = self.simpack_grokker.get_step_iterator(history_browser,
                                                          step_profile)
        finite_iterator = cute_iter_tools.shorten(iterator, iterations)
        finite_iterator_with_lock = cute_iter_tools.iter_with(
            finite_iterator,
            self.tree.lock.write
        )
        
        current_node = node
        
        yield current_node
        
        try:
            for current_state in finite_iterator_with_lock:
                                
                current_node = self.tree.add_state(current_state,
                                                   parent=current_node,
                                                   step_profile=step_profile)
                
                history_browser.tail_node = current_node
                history_browser.path = current_node.make_containing_path()
                # Similarly to the `__history_dependent_simulate` method, here
                # we also need to recreate the path. But in this case we need to
                # do it not only on the first run, but on *each* run of the
                # loop, because this is a generator, and the user may wreak
                # havoc with the tree between `yield`s, causing our original
                # path not to lead to the tail_node anymore.                
                # todo optimize: The fact we recreate a path every time might be
                # costly.
                    
                yield current_node
        
        except garlicsim.misc.WorldEnded:
            self.tree.make_end(current_node, step_profile)
                
    
    def __non_history_dependent_iter_simulate(self, node, iterations,
                                              step_profile=None):
        '''
        Simulate from the given node for the given number of iterations.
        
        (Internal function for non-history-dependent simulations only.)
        
        The results are implemented into the tree. Note that the crunching for
        this is done synchronously, i.e. in the currrent thread.
        
        This returns a generator that yields all the nodes one-by-one, from the
        initial node to the final one.
        
        A step profile may be passed to be used with the step function.
        '''
        
        if step_profile is None:
            step_profile = self.build_step_profile()

        state = node.state
                
        iterator = self.simpack_grokker.get_step_iterator(state, step_profile)
        finite_iterator = cute_iter_tools.shorten(iterator, iterations)
        finite_iterator_with_lock = cute_iter_tools.iter_with(
            finite_iterator,
            self.tree.lock.write
        )
        
        current_node = node
        
        yield current_node
        
        try:
            for current_state in finite_iterator_with_lock:
                current_node = self.tree.add_state(current_state,
                                                   parent=current_node,
                                                   step_profile=step_profile)
                yield current_node
        
        except garlicsim.misc.WorldEnded:
            self.tree.make_end(current_node, step_profile)
            
    
    def __getstate__(self):
        project_vars = dict(self.__dict__)
        
        del project_vars['crunching_manager']
        del project_vars['simpack_grokker']
        
        project_vars['___cruncher_type_of_crunching_manager'] = \
            self.crunching_manager.cruncher_type
        
        return project_vars
    
    
    def __setstate__(self, project_vars):
        self.__init__(project_vars["simpack"])
        self.__dict__.update(project_vars)
        self.crunching_manager.cruncher_type = \
            project_vars['___cruncher_type_of_crunching_manager']
            
        
        
    def __repr__(self):
        '''
        Get a string representation of the project.
        
        Example output:
        
        <garlicsim.Project containing 101 nodes and employing 4 crunchers at
        0x1f668d0>
        '''
        # Todo: better have the simpack mentioned here, not doing it cause it's
        # currently in a module wrapper.
        
        # todo: show cruncher types, even listing for different types if there
        # are different types. Length is not a problem because this is a rare
        # condition.
        
        nodes_count = len(self.tree.nodes)
        crunchers_count = len(self.crunching_manager.crunchers)
                                   
        return '<%s containing %s nodes and employing %s crunchers at %s>' % \
               (
                   address_tools.describe(type(self), shorten=True),
                   nodes_count,
                   crunchers_count,
                   hex(id(self))
               )
        
    
    def build_step_profile(self, *args, **kwargs):
        '''
        there's one here in addition to that in the simpack grokker because the default step function here can be changed
        '''
        parse_arguments_to_step_profile = \
            garlicsim.misc.StepProfile.build_parser(
                self.default_step_function
            )
        
        step_profile = parse_arguments_to_step_profile(*args, **kwargs)
        return step_profile
        
        
        
        
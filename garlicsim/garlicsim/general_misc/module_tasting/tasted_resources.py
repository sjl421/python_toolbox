# Copyright 2009-2011 Ram Rachum.
# This program is distributed under the LGPL2.1 license.

'''
This module defines the `` class.

See its documentation for more information.
'''

import sys

import pkg_resources


from .module_tasting import taste_module


def get_provider(module_name_or_req):
    """Get an `IResourceProvider` for the named module or requirement"""
    if isinstance(module_name_or_req, pkg_resources.Requirement):
        return pkg_resources.working_set.find(module_name_or_req) or \
                              pkg_resources.require(str(module_name_or_req))[0]
    try:
        tasted_module = sys.modules[module_name_or_req]
    except KeyError:
        tasted_module = taste_module(module_name_or_req)
    loader = getattr(tasted_module, '__loader__', None)
    adapter = pkg_resources._find_adapter(
        pkg_resources._provider_factories,
        loader
    )
    return adapter(tasted_module)


def resource_exists(self, package_or_requirement, resource_name):
    '''Does the named resource exist?'''
    return get_provider(package_or_requirement).has_resource(resource_name)


def resource_isdir(self, package_or_requirement, resource_name):
    '''Is the named resource an existing directory?'''
    return get_provider(package_or_requirement).resource_isdir(
      resource_name
    )


def resource_filename(self, package_or_requirement, resource_name):
    '''Return a true filesystem path for specified resource.'''
    return get_provider(package_or_requirement).get_resource_filename(
      self, resource_name
    )


def resource_stream(self, package_or_requirement, resource_name):
    '''Return a readable file-like object for specified resource.'''
    return get_provider(package_or_requirement).get_resource_stream(
      self, resource_name
    )


def resource_string(self, package_or_requirement, resource_name):
    '''Return specified resource as a string.'''
    return get_provider(package_or_requirement).get_resource_string(
      self, resource_name
    )


def resource_listdir(self, package_or_requirement, resource_name):
    '''List the contents of the named resource directory.'''
    return get_provider(package_or_requirement).resource_listdir(
      resource_name
    )
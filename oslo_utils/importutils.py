#!/usr/bin/env python
# encoding: utf-8
import sys
import traceback

def import_object(import_str, *args, **kwargs):
    """Import a class and return an instance of it.

    .. versionadded:: 0.3
    """
    return import_class(import_str)(*args, **kwargs)


def import_class(import_str):
    """Returns a class from a string including module and class.

    .. versionadded:: 0.3
    """
    mod_str, _sep, class_str = import_str.rpartition('.')
    __import__(mod_str)
    try:
        return getattr(sys.modules[mod_str], class_str)
    except AttributeError:
        raise ImportError('Class %s cannot be found (%s)' %
                          (class_str,
                           traceback.format_exception(*sys.exc_info())))

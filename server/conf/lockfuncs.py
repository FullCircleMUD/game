"""

Lockfuncs

Lock functions are functions available when defining lock strings,
which in turn limits access to various game systems.

All functions defined globally in this module are assumed to be
available for use in lockstrings to determine access. See the
Evennia documentation for more info on locks.

A lock function is always called with two arguments, accessing_obj and
accessed_obj, followed by any number of arguments. All possible
arguments should be handled with *args, **kwargs. The lock function
should handle all eventual tracebacks by logging the error and
returning False.

Lock functions in this module extend (and will overload same-named)
lock functions from evennia.locks.lockfuncs.

"""

def is_ooc(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Lock: returns True if the accessing account is NOT currently puppeting
    a character (i.e. is at the OOC menu).

    Usage in lock string: cmd:is_ooc()
    """
    if hasattr(accessing_obj, "get_all_puppets"):
        return not accessing_obj.get_all_puppets()
    return False

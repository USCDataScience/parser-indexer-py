from __future__ import print_function


from six import add_metaclass
from abc import ABCMeta, abstractmethod


@add_metaclass(ABCMeta)
class Parser(object):
    def __init__(self, parser_name):
        self.parse_name = parser_name

    @abstractmethod
    def parse(self, *args):
        raise RuntimeError('This is abstract method that must be implemented '
                           'in sub-classes')

















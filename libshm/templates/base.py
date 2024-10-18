import ctypes
from abc import ABCMeta, abstractmethod, ABC
from typing import Any

from auv_python_helpers import load_library
auv_var_lib = load_library("libauvshm.so")

class ShmGrp(ctypes.Structure):
    """ Base class for python shared memory groups, useful for type hinting.
    """
    pass

class ShmVar(object):
    __metaclass__ = ABCMeta
    """ Base class for python shared memory variables """

    @classmethod
    @abstractmethod
    def get(cls) -> Any:
        """reads shared memory var

        Returns:
            Any: python native type
        """
        raise NotImplementedError('ShmVar.get')

    @classmethod
    @abstractmethod
    def set(cls, value: Any):
        """sets shared memory var

        Args:
            value (Any): python native type
        """
        raise NotImplementedError('ShmVar.set')

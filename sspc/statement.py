from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from sspc.expression import compile_expression


class Statement(metaclass=ABCMeta):
    @abstractmethod
    def compile(self, context):
        pass


@dataclass
class LetStmt(Statement):
    name: str
    value: Any
    dtype: Optional[Any] = None

    def compile(self, context):
        dtype = context.find_type(self.dtype) if self.dtype is not None else None
        value = compile_expression(self.value, context, type_hint=dtype)
        context.register(self.name, value)


@dataclass
class ReturnStmt(Statement):
    value: Optional[Any]

    def compile(self, context):
        if self.value is None:
            context.builder.ret_void()
        else:
            context.builder.ret(compile_expression(self.value, context, type_hint=context.func.ftype.return_type))

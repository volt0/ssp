from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from sspc.datatypes import Boolean
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
class IfStmt(Statement):
    condition: Any
    then_body: Any
    else_body: Any = None

    def compile(self, context):
        condition = compile_expression(self.condition, context, type_hint=Boolean())
        if self.else_body is not None:
            with context.builder.if_else(condition) as (then, otherwise):
                with then:
                    for stmt in self.then_body:
                        stmt.compile(context)
                with otherwise:
                    for stmt in self.else_body:
                        stmt.compile(context)
        else:
            with context.builder.if_then(condition):
                for stmt in self.then_body:
                    stmt.compile(context)


@dataclass
class ReturnStmt(Statement):
    value: Optional[Any]

    def compile(self, context):
        if self.value is None:
            context.builder.ret_void()
        else:
            context.builder.ret(compile_expression(self.value, context, type_hint=context.func.ftype.return_type))

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, List

from llvmlite import ir

from sspc.datatypes import coerce, Type, Boolean
from sspc.errors import OperationNotAllowed, UnknownIdentifierError


def compile_expression(node, context, *, type_hint=None):
    if isinstance(node, ir.Constant):
        result = node

    elif isinstance(node, str):
        result = context.find(node)
        if result is None:
            raise UnknownIdentifierError(node)

    elif isinstance(node, Expression):
        result = node.compile(context)

    else:
        raise NotImplementedError()

    if type_hint is not None:
        result = coerce(type_hint, result, context)

    return result


class Expression(metaclass=ABCMeta):
    @abstractmethod
    def compile(self, context):
        pass


class OpUnaryType(Enum):
    PLUS = 0
    MINUS = 1
    BITWISE_NOT = 2
    LOGICAL_NOT = 3

    def describe(self):
        if self == OpUnaryType.PLUS:
            return 'unary +'
        elif self == OpUnaryType.MINUS:
            return 'unary -'
        elif self == OpUnaryType.BITWISE_NOT:
            return '~'
        elif self == OpUnaryType.LOGICAL_NOT:
            return '!'


@dataclass
class OpUnary(Expression):
    x: Any
    operation: OpUnaryType

    def compile(self, context):
        args_type_hint = None
        if self.operation == OpUnaryType.LOGICAL_NOT:
            args_type_hint = Boolean()

        x = compile_expression(self.x, context, type_hint=args_type_hint)
        result = x.type.op_unary(self.operation, x, context)
        if result is None:
            raise OperationNotAllowed.for_unary_op(self.operation, x.type)
        return result


class OpBinaryType(Enum):
    ADD = 0
    SUB = 1
    MUL = 2
    DIV = 3
    MOD = 4
    BITWISE_AND = 5
    BITWISE_XOR = 6
    BITWISE_OR = 7

    EQ = 8
    LT = 9
    GT = 10
    LE = 11
    GE = 12
    NE = 13

    LOGICAL_AND = 14
    LOGICAL_OR = 15

    def describe(self):
        if self == OpBinaryType.ADD:
            return '+'
        elif self == OpBinaryType.SUB:
            return '-'
        elif self == OpBinaryType.MUL:
            return '*'
        elif self == OpBinaryType.DIV:
            return '/'
        elif self == OpBinaryType.MOD:
            return '%'
        elif self == OpBinaryType.BITWISE_AND:
            return '&'
        elif self == OpBinaryType.BITWISE_XOR:
            return '^'
        elif self == OpBinaryType.BITWISE_OR:
            return '|'
        elif self == OpBinaryType.EQ:
            return '=='
        elif self == OpBinaryType.LT:
            return '<'
        elif self == OpBinaryType.GT:
            return '>'
        elif self == OpBinaryType.LE:
            return '<='
        elif self == OpBinaryType.GE:
            return '>='
        elif self == OpBinaryType.NE:
            return '!='
        elif self == OpBinaryType.LOGICAL_AND:
            return '&&'
        elif self == OpBinaryType.LOGICAL_OR:
            return '||'


@dataclass
class OpBinary(Expression):
    a: Any
    b: Any
    operation: OpBinaryType

    def compile(self, context):
        args_type_hint = None
        if self.operation in (OpBinaryType.LOGICAL_OR, OpBinaryType.LOGICAL_AND):
            args_type_hint = Boolean()

        a = compile_expression(self.a, context, type_hint=args_type_hint)
        b = compile_expression(self.b, context, type_hint=args_type_hint)
        result = a.type.op_binary(self.operation, a, b, context)
        if result is None:
            raise OperationNotAllowed.for_binary_op(self.operation, a.type, b.type)
        return result


@dataclass
class Call(Expression):
    func: Any
    args: List[Any]

    def compile(self, context):
        f = compile_expression(self.func, context)
        if isinstance(f, Type) and f.has_explicit_cast:
            assert len(self.args) == 1
            return f.explicit_cast(compile_expression(self.args[0], context), context)

        args = [compile_expression(arg, context) for arg in self.args]
        return context.builder.call(f, args)

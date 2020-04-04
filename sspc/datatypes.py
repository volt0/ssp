from llvmlite import ir as ir
from wrapt import CallableObjectProxy

from sspc.errors import TypeMismatch


def coerce(target_type, value, context):
    value_type = value.type

    if isinstance(target_type, Boolean):
        if isinstance(value_type, Integer):
            result = context.builder.icmp_unsigned('!=', value, value_type(0))
            result = context.builder.zext(result, target_type)
            result.type = target_type
            return result
        else:
            return ir.Constant(Boolean(), 1)

    elif value_type == target_type:
        if value_type is not target_type:
            value.type = target_type
        return value

    elif isinstance(target_type, Integer):
        if isinstance(value_type, Integer) and target_type.is_unsigned == value_type.is_unsigned:
            if value_type.width < target_type.width:
                if target_type.is_unsigned:
                    return context.builder.zext(value, target_type)
                else:
                    return context.builder.sext(value, target_type)
        elif isinstance(value_type, Boolean):
            return context.builder.zext(value, target_type)

    # print(value, '\n:', type(value_type), 'as', type(target_type))
    raise TypeMismatch('Cannot assign %s to %s' % (value_type, target_type))


class Type:
    has_explicit_cast = False

    def explicit_cast(self, value, context):
        raise NotImplementedError()

    def op_unary(self, operation, x, context):
        pass

    def op_binary(self, operation, a, b, context):
        pass


class Integer(CallableObjectProxy, Type):
    is_unsigned = None
    has_explicit_cast = True

    def __init__(self, bits, is_unsigned):
        super().__init__(ir.IntType(bits))
        self.is_unsigned = is_unsigned

    def explicit_cast(self, value, context):
        value_type = value.type
        if value_type == self:
            if value_type is not self:
                value.type = self
            return value

        elif isinstance(value_type, Integer):
            value_width = value_type.width
            target_width = self.width

            if value_width > target_width:
                return context.builder.trunc(value, self)
            elif value_width < target_width:
                if self.is_unsigned:
                    return context.builder.zext(value, self)
                else:
                    return context.builder.sext(value, self)

        elif isinstance(value_type, Boolean):
            return context.builder.zext(value, self)

        raise TypeMismatch('Cannot cast %s to %s' % (value_type, self))

    def op_unary(self, operation, x, context):
        from sspc.expression import OpUnaryType

        if not self.is_unsigned:
            if operation == OpUnaryType.PLUS:
                return x
            elif operation == OpUnaryType.MINUS:
                return context.builder.neg(x)
            elif operation == OpUnaryType.BITWISE_NOT:
                return context.builder.not_(x)

    def op_binary(self, operation, a, b, context):
        from sspc.expression import OpBinaryType

        if isinstance(b.type, Integer) and self.is_unsigned == b.type.is_unsigned:
            if b.type.width > self.width:
                b, a = a, b
            b = coerce(a.type, b, context)

            if operation == OpBinaryType.ADD:
                return context.builder.add(a, b)
            elif operation == OpBinaryType.SUB:
                return context.builder.sub(a, b)
            elif operation == OpBinaryType.MUL:
                return context.builder.mul(a, b)
            elif operation == OpBinaryType.DIV:
                if self.is_unsigned:
                    return context.builder.udiv(a, b)
                else:
                    return context.builder.sdiv(a, b)
            elif operation == OpBinaryType.MOD:
                if self.is_unsigned:
                    return context.builder.urem(a, b)
                else:
                    return context.builder.srem(a, b)
            elif operation == OpBinaryType.BITWISE_AND:
                return context.builder.and_(a, b)
            elif operation == OpBinaryType.BITWISE_XOR:
                return context.builder.xor(a, b)
            elif operation == OpBinaryType.BITWISE_OR:
                return context.builder.or_(a, b)
            elif operation == OpBinaryType.EQ:
                return self.op_comparison('==', a, b, context)
            elif operation == OpBinaryType.LT:
                return self.op_comparison('<', a, b, context)
            elif operation == OpBinaryType.GT:
                return self.op_comparison('>', a, b, context)
            elif operation == OpBinaryType.LE:
                return self.op_comparison('<=', a, b, context)
            elif operation == OpBinaryType.GE:
                return self.op_comparison('>=', a, b, context)
            elif operation == OpBinaryType.NE:
                return self.op_comparison('!=', a, b, context)

    def op_comparison(self, operation, a, b, context):
        if self.is_unsigned:
            result = context.builder.icmp_unsigned(operation, a, b)
        else:
            result = context.builder.icmp_signed(operation, a, b)

        result.type = Boolean()
        return result


class Boolean(CallableObjectProxy, Type):
    has_explicit_cast = True

    def __init__(self):
        super().__init__(ir.IntType(1))

    def explicit_cast(self, value, context):
        return coerce(Boolean(), value, context)

    def op_unary(self, operation, x, context):
        from sspc.expression import OpUnaryType

        if operation == OpUnaryType.LOGICAL_NOT:
            return context.builder.not_(x)

    def op_binary(self, operation, a, b, context):
        from sspc.expression import OpBinaryType

        if operation == OpBinaryType.LOGICAL_AND:
            return context.builder.and_(a, b)
        elif operation == OpBinaryType.LOGICAL_OR:
            return context.builder.or_(a, b)


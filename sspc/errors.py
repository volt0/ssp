class CompileError(Exception):
    pass


class DuplicatedNameError(CompileError):
    pass


class UnknownIdentifierError(CompileError):
    def __init__(self, node):
        super().__init__('Unknown identifier "%s"' % node)


class TypeMismatch(CompileError):
    pass


class OperationNotAllowed(CompileError):
    @classmethod
    def for_unary_op(cls, operation, value_type):
        return cls('Operation "%s" is not allowed for %s' % (operation.describe(), value_type))

    @classmethod
    def for_binary_op(cls, operation, a_type, b_type):
        return cls('Operation "%s" is not allowed for %s and %s' % (operation.describe(), a_type, b_type))

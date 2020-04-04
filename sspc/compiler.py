import llvmlite.ir as ir

import sspc.datatypes
from sspc import ast, datatypes
from sspc.context import Context, FunctionContext


def compile_function(function_ast, module, parent_context):
    return_type = (
        ir.VoidType()
        if function_ast.return_type is None
        else parent_context.find_type(function_ast.return_type)
    )
    func_type = ir.FunctionType(return_type, [parent_context.find_type(arg.type) for arg in function_ast.arguments])
    func = ir.Function(module, func_type, name=function_ast.name)
    parent_context.register(function_ast.name, func)

    bb_entry = func.append_basic_block()
    builder = ir.IRBuilder()
    builder.position_at_end(bb_entry)

    for arg, arg_ast in zip(func.args, function_ast.arguments):
        arg.name = arg_ast.name

    context = FunctionContext(parent_context, builder=builder, func=func)
    if function_ast.body:
        for stmt in function_ast.body:
            stmt.compile(context)

        last_block = context.builder.function.blocks[-1]
        if not len(last_block.instructions):
            context.builder.function.blocks.pop()
    else:
        context.builder.ret_void()

    return func


def compile_module(module_ast: ast.module):
    module = ir.Module('test')
    context = Context()
    context.symbols = {
        'ubyte': datatypes.Integer(8, True),
        'ushort': datatypes.Integer(16, True),
        'uint': datatypes.Integer(32, True),
        'ulong': datatypes.Integer(64, True),
        'byte': datatypes.Integer(8, False),
        'short': datatypes.Integer(16, False),
        'int': datatypes.Integer(32, False),
        'long': datatypes.Integer(64, False),
        'bool': sspc.datatypes.Boolean(),
    }

    for decl in module_ast.declarations:
        if isinstance(decl, ast.function_declaration):
            compile_function(decl, module, context)

    return module

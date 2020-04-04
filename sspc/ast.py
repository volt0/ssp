from collections import namedtuple

module = namedtuple('Module', ['declarations'])
function_declaration = namedtuple('FunctionDeclaration', ['name', 'arguments', 'return_type', 'body'])
argument = namedtuple('Argument', ['name', 'type'])

assign = namedtuple('Assign', ['l', 'r'])

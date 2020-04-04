from collections import deque

import llvmlite.ir as ir
from ply import lex, yacc

from sspc import ast, statement, expression, datatypes

keywords = {
    'def': 'DEF',
    'var': 'VAR',
    'let': 'LET',
    'if': 'IF',
    'else': 'ELSE',
    'for': 'FOR',
    'pass': 'PASS',
    'return': 'RETURN',
    'true': 'TRUE',
    'false': 'FALSE',
}

tokens = (
    *keywords.values(),
    'ID',
    'INTEGER',
    'FLOAT',
    'STRING',
    'ASSIGN',
    'PLUS',
    'MINUS',
    'BANG',
    'TILDE',
    'MUL',
    'DIV',
    'MOD',
    'BITWISE_AND',
    'BITWISE_XOR',
    'BITWISE_OR',
    'LOGICAL_AND',
    'LOGICAL_OR',
    'LPAREN',
    'RPAREN',
    'LT',
    'LE',
    'GT',
    'GE',
    'NE',
    'EQ',
    'COMMA',
    'COLON',
    'SEMI',
    'ARROW',
    'NEWLINE',
    'INDENT',
    'DEDENT',
    'EOF',
)

t_ASSIGN = r'='
t_PLUS = r'\+'
t_MINUS = r'-'
t_MUL = r'\*'
t_DIV = r'/'
t_MOD = r'%'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LT = r'<'
t_LE = r'<='
t_GT = r'>'
t_GE = r'>='
t_EQ = r'=='
t_NE = r'!='
t_BITWISE_AND = r'&'
t_BITWISE_XOR = r'\^'
t_BITWISE_OR = r'\|'
t_LOGICAL_AND = r'&&'
t_LOGICAL_OR = r'\|\|'
t_BANG = r'!'
t_TILDE = r'~'
t_COMMA = r'\,'
t_COLON = r':'
t_SEMI = r';'
t_ARROW = r'->'

t_ignore = " \t"


def t_ID(t):
    r"""[_a-zA-Z][_a-zA-Z0-9]*"""
    keyword_type = keywords.get(t.value)
    if keyword_type is not None:
        t.type = keyword_type
    return t


def t_INTEGER(t):
    r"""\d+"""
    t.value = int(t.value)
    return t


def t_FLOAT(t):
    r"""((\d*\.\d+)([Ee][+-]?\d+)?|([1-9]\d*[Ee][+-]?\d+))"""
    t.value = float(t.value)
    return t


def t_STRING(t):
    r"""\".*?\""""
    t.value = t.value[1:-1]
    return t


def t_newline(t):
    r"""\n+"""
    t.lexer.lineno += len(t.value)
    t.type = "NEWLINE"
    if t.lexer.paren_count == 0:
        return t


def t_comment(t):
    r"""\s*\043[^\n]*"""
    pass


def t_error(t):
    print('Illegal character "%s"' % t.value)
    t.lexer.skip(1)


def p_translation_unit(p):
    """
    translation_unit : translation_unit declaration
                     | declaration
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[1].append(p[2])
        p[0] = p[1]


def p_translation_unit_eof(p):
    """translation_unit : translation_unit EOF"""
    p[0] = p[1]


def p_declaration(p):
    """declaration : function_declaration"""
    p[0] = p[1]


def p_function_declaration(p):
    """function_declaration : DEF ID LPAREN arglist RPAREN function_return_type COLON compound_stmt"""
    p[0] = ast.function_declaration(p[2], p[4], p[6], p[8])


def p_arglist_empty(p):
    """arglist :"""
    p[0] = []


def p_arglist(p):
    """
    arglist : arglist COMMA argument
            | argument
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[1].append(p[3])
        p[0] = p[1]


def p_argument(p):
    """argument : ID COLON type"""
    p[0] = ast.argument(p[1], p[3])


def p_function_return_type(p):
    """function_return_type : ARROW type"""
    p[0] = p[2]


def p_function_return_type_void(p):
    """function_return_type :"""
    # TODO: -> void
    p[0] = None


def p_compound_stmt(p):
    """compound_stmt : INDENT stmt_list DEDENT"""
    p[0] = p[2]


def p_compound_stmt_empty(p):
    """compound_stmt : INDENT PASS DEDENT"""
    p[0] = []


def p_stmt_list(p):
    """
    stmt_list : stmt_list NEWLINE stmt
              | stmt_list stmt_list
              | stmt
    """
    if len(p) == 2:
        p[0] = [p[1]]
    elif len(p) == 3:
        p[1].extend(p[2])
        p[0] = p[1]
    else:
        p[1].append(p[3])
        p[0] = p[1]


def p_stmt_1(p):
    """
    stmt : expression
         | assignment
         | let
         | if
         | return
    """
    p[0] = p[1]


def p_let(p):
    """
    let : LET ID COLON type ASSIGN expression
        | LET ID ASSIGN expression
    """
    if len(p) == 7:
        p[0] = statement.LetStmt(name=p[2], value=p[6], dtype=p[4])
    else:
        p[0] = statement.LetStmt(name=p[2], value=p[4])


def p_if(p):
    """
    if : IF expression COLON compound_stmt
    """
    p[0] = statement.IfStmt(condition=p[2], then_body=p[4])


def p_if_else(p):
    """
    if : IF expression COLON compound_stmt ELSE COLON compound_stmt
    """
    p[0] = statement.IfStmt(condition=p[2], then_body=p[4], else_body=p[7])


def p_return(p):
    """
    return : RETURN expression
           | RETURN
    """
    p[0] = statement.ReturnStmt(p[2] if len(p) == 3 else None)


def p_assignment(p):
    """assignment : lvalue ASSIGN expression"""
    p[0] = ast.assign(p[2], p[4])


unary_ops = {
    '+': expression.OpUnaryType.PLUS,
    '-': expression.OpUnaryType.MINUS,
}

binary_ops = {
    '+': expression.OpBinaryType.ADD,
    '-': expression.OpBinaryType.SUB,
    '*': expression.OpBinaryType.MUL,
    '/': expression.OpBinaryType.DIV,
    '%': expression.OpBinaryType.MOD,
    '&': expression.OpBinaryType.BITWISE_AND,
    '^': expression.OpBinaryType.BITWISE_XOR,
    '|': expression.OpBinaryType.BITWISE_OR,
    '==': expression.OpBinaryType.EQ,
    '<': expression.OpBinaryType.LT,
    '>': expression.OpBinaryType.GT,
    '<=': expression.OpBinaryType.LE,
    '>=': expression.OpBinaryType.GE,
    '!=': expression.OpBinaryType.NE,
    '&&': expression.OpBinaryType.LOGICAL_AND,
    '||': expression.OpBinaryType.LOGICAL_OR,
}

precedence = (
    ('left', 'LOGICAL_OR'),
    ('left', 'LOGICAL_AND'),
    ('left', 'LT', 'LE', 'GT', 'GE', 'EQ', 'NE'),
    ('left', 'BITWISE_OR', 'BITWISE_XOR'),
    ('left', 'BITWISE_AND'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'MUL', 'DIV', 'MOD'),
    ('right', 'LOGICAL_NOT'),
    ('right', 'UNARY_PLUS', 'UNARY_MINUS', 'BITWISE_NOT'),
)


def p_expression(p):
    """
    expression : rvalue
    """
    p[0] = p[1]


def p_expression_op_unary(p):
    """
    expression : PLUS expression %prec UNARY_PLUS
               | MINUS expression %prec UNARY_MINUS
               | TILDE expression %prec BITWISE_NOT
               | BANG expression %prec LOGICAL_NOT

    """
    p[0] = expression.OpUnary(x=p[2], operation=unary_ops.get(p[1]))


def p_expression_op_binary(p):
    """
    expression : expression PLUS expression
               | expression MINUS expression
               | expression MUL expression
               | expression DIV expression
               | expression MOD expression
               | expression BITWISE_AND expression
               | expression BITWISE_XOR expression
               | expression BITWISE_OR expression
               | expression EQ expression
               | expression LT expression
               | expression GT expression
               | expression LE expression
               | expression GE expression
               | expression NE expression
               | expression LOGICAL_AND expression
               | expression LOGICAL_OR expression
    """
    p[0] = expression.OpBinary(a=p[1], b=p[3], operation=binary_ops.get(p[2]))


def p_expression_call(p):
    """expression : rvalue LPAREN expression_list RPAREN"""
    p[0] = expression.Call(p[1], p[3])


def p_expression_list_empty(p):
    """expression_list :"""
    p[0] = []


def p_expression_list(p):
    """
    expression_list : expression_list COMMA expression
                    | expression
    """
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[1].append(p[3])
        p[0] = p[1]


def p_rvalue_int_literal(p):
    """
    rvalue : INTEGER
    """
    p[0] = ir.Constant(datatypes.Integer(32, False), p[1])


# def p_rvalue_float_literal(p):
#     """
#     rvalue : FLOAT
#     """
#     p[0] = p[1]

# def p_rvalue_literal(p):
#     """
#     rvalue : STRING
#     """
#     p[0] = p[1]


def p_rvalue_true(p):
    """rvalue : TRUE"""
    p[0] = ir.Constant(datatypes.Boolean(), 1)


def p_rvalue_false(p):
    """rvalue : FALSE"""
    p[0] = ir.Constant(datatypes.Boolean(), 0)


def p_rvalue_parentheses(p):
    """rvalue : LPAREN expression RPAREN"""
    p[0] = p[2]


def p_rvalue_variable(p):
    """rvalue : ID"""
    p[0] = p[1]


def p_lvalue_variable(p):
    """lvalue : ID"""
    p[0] = p[1]


def p_type(p):
    """type : ID"""
    p[0] = p[1]


def p_error(p):
    raise SyntaxError(p)


class Lexer:
    def __init__(self, debug=False):
        self.debug = debug
        self.lexer = lex.lex()
        self.token_stream = iter(())

    def input(self, s):
        self.lexer.paren_count = 0
        self.lexer.input(s)
        self.token_stream = self.process_tokens(self.lexer)

    def process_tokens(self, stream):
        def emit_token(token_type, lexpos, lineno, value=None):
            indent_token = lex.LexToken()
            indent_token.type = token_type
            indent_token.value = value
            indent_token.lineno = lineno
            indent_token.lexpos = lexpos
            return indent_token

        prev_token = None
        prev_indent = 0
        line_start_lexpos = 0
        indent_stack = deque()
        for token in stream:
            if token.type == 'NEWLINE':
                line_start_lexpos = token.lexpos + len(token.value)
                if prev_token is None:
                    continue

            else:
                cur_indent = token.lexpos - line_start_lexpos
                if prev_token is None:
                    if cur_indent > prev_indent:
                        yield emit_token('INDENT', token.lexpos, token.lineno)

                elif prev_token.type == 'NEWLINE':
                    is_indent_changed = False
                    if cur_indent > prev_indent:
                        is_indent_changed = True
                        yield emit_token('INDENT', line_start_lexpos, token.lineno)
                        indent_stack.append(prev_indent)
                        prev_indent = cur_indent

                    else:
                        while cur_indent < prev_indent:
                            if len(indent_stack):
                                is_indent_changed = True
                                prev_indent = indent_stack.pop()
                                yield emit_token('DEDENT', line_start_lexpos, token.lineno)

                    if not is_indent_changed:
                        yield prev_token

                yield token

            prev_token = token

        if len(indent_stack) and prev_token is not None:
            for _ in indent_stack:
                yield emit_token('DEDENT', self.lexer.lexpos, self.lexer.lineno)

        yield emit_token('EOF', self.lexer.lexpos, self.lexer.lineno)

    def token(self):
        try:
            token = next(self.token_stream)
            if self.debug:
                print(token)
            return token
        except StopIteration:
            return None


class Parser(object):
    def __init__(self, debug=False):
        self.debug = debug
        self.lexer = Lexer(debug=self.debug)
        self.parser = yacc.yacc(start='translation_unit')

    def parse(self, code):
        self.lexer.input(code)
        result = self.parser.parse(lexer=self.lexer, debug=self.debug)
        return ast.module(result)

        # while True:
        #     t = self.lexer.token()
        #     if not t:
        #         break
        #     print(t)

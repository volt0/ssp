from collections import deque, defaultdict

from sspc.errors import CompileError, DuplicatedNameError


class Context:
    def __init__(self, parent=None):
        self.parent = parent
        self.symbols = {}
        self._imports = deque()
        self._basename_map = defaultdict(int)

    def is_used(self, name):
        return any(result is not None for result in self._search_sequence(name))

    def find(self, name):
        for result in self._search_sequence(name):
            if result is not None:
                return result
        return None

    def find_type(self, name):
        result = self.find(name)
        if result is None:
            raise CompileError('Undefined type %s' % name)
        return result

    def register(self, name, symbol, deduplicate=False):
        if deduplicate:
            name = self.deduplicate(name)
        elif self.is_used(name):
            raise DuplicatedNameError(name)

        self.symbols[name] = symbol
        return name

    def deduplicate(self, name):
        basename = name
        while self.is_used(name):
            ident = self._basename_map[basename] + 1
            self._basename_map[basename] = ident
            name = "{0}.{1}".format(basename, ident)
        return name

    def _search_sequence(self, name):
        yield self.symbols.get(name)

        for mod in reversed(self._imports):
            yield mod.find(name)

        if self.parent is not None:
            yield self.parent.find(name)

    def __getattr__(self, item):
        if self.parent is None:
            raise AttributeError(item)

        return getattr(self.parent, item)


class FunctionContext(Context):
    def __init__(self, parent, *, builder, func):
        super().__init__(parent=parent)
        self.builder = builder
        self.func = func

        for arg in func.args:
            self.register(arg.name, arg)

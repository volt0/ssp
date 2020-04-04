import subprocess

import llvmlite.binding as llvm

from sspc.compiler import compile_module
from sspc.parser.parser import Parser


def main():
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    parser = Parser(debug=False)
    with open('test.ssp') as fp:
        module_ast = parser.parse(fp.read())
        module_ir = compile_module(module_ast)
        print(module_ast)

    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    module_ir.triple = target_machine.triple
    module_ir.data_layout = target_machine.target_data
    module_ir_raw = str(module_ir).encode()
    with open('test.ll', 'wb') as fp:
        fp.write(module_ir_raw)

    with open('test.o', 'wb') as fp:
        subprocess.run(['llc', '-filetype=obj', '-'], input=module_ir_raw, stdout=fp)
        fp.write(b'\0' * 512)

    subprocess.run(['gcc', 'test.o', '-o', 'test'])
    # subprocess.run(['ld', 'test.o', '-o', 'test'])


if __name__ == '__main__':
    main()

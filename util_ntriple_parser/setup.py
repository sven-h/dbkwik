from distutils.core import setup
from Cython.Build import cythonize
from distutils.extension import Extension


#from Cython.Compiler.Options import _directive_defaults
#_directive_defaults['linetrace'] = True
#_directive_defaults['binding'] = True


#extensions =[
#    Extension('nparser', ["nparser.pyx"], language='c++',extra_compile_args=["-Zi", "/Od"], extra_link_args=["-debug"]) # , define_macros=[('CYTHON_TRACE', '1')] , libraries=["zlib"]
    #for debugging code in visual studio: ,extra_compile_args=["-Zi", "/Od"], extra_link_args=["-debug"]

#]

ext_options = {"compiler_directives": {"profile": True}, "annotate": True, "gdb_debug":True, "language":"c++"}
setup(
    name='nparser',
    version='1.0',
    description='Parser for ntriples',
    author='Sven Hertling',
    #ext_modules = cythonize(extensions)#"nparser.pyx")#, **ext_options)
    ext_modules = cythonize(Extension('nparser', ["nparser.pyx"], language='c++'))
)

#https://github.com/cython/cython/wiki/DebuggingTechniques
import setuptools
import sys
try:
    import distutils.ccompiler
except ImportError:
    try:
        import _distutils_hack
        _distutils_hack.do_override()
    except ImportError:
        pass

from tree_sitter import Language

Language.build_library(
  'build/languages.so',
  [
    'vendor/grammars/tree-sitter-python',
    'vendor/grammars/tree-sitter-javascript',
    'vendor/grammars/tree-sitter-typescript/typescript',
  ]
)
print("Successfully built languages.so")

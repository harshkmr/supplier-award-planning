"""setup.py — needed for C extension compilation via setuptools."""

import platform
from setuptools import setup, Extension

# MSVC uses /W4 for high warnings; GCC/Clang use -Wall -Wextra
if platform.system() == "Windows":
    extra_compile_args = ["/W4"]
else:
    extra_compile_args = ["-Wall", "-Wextra"]

container_util = Extension(
    "supplier_award._container_util",
    sources=["src/_container_util.c"],
    extra_compile_args=extra_compile_args,
)

setup(
    ext_modules=[container_util],
)

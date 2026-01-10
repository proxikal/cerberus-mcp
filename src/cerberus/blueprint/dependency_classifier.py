"""Dependency classification for distinguishing internal, external, and stdlib code.

Phase 13.5: Classify dependencies to prevent agents from editing third-party code.
"""

import sys
import sysconfig
from pathlib import Path
from typing import Optional, Literal

from cerberus.logging_config import logger


DependencyType = Literal["internal", "external", "stdlib"]


class DependencyClassifier:
    """Classifies dependencies as internal, external (third-party), or stdlib."""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize dependency classifier.

        Args:
            project_root: Project root directory (defaults to cwd)
        """
        self.project_root = project_root or Path.cwd()
        self._stdlib_paths = self._get_stdlib_paths()
        self._third_party_indicators = [
            'site-packages',
            'dist-packages',
            '.venv',
            'venv',
            'virtualenv',
            'node_modules',
            'vendor',
        ]

    def classify_dependency(
        self,
        target_symbol: str,
        target_file: Optional[str] = None
    ) -> DependencyType:
        """
        Classify a dependency as internal, external, or stdlib.

        Args:
            target_symbol: Symbol name (e.g., "os.path.join", "stripe.charge")
            target_file: Optional file path where target is defined

        Returns:
            Classification: "internal", "external", or "stdlib"
        """
        # If we have a target file path, use it for classification
        if target_file:
            return self._classify_by_file(target_file)

        # Otherwise, classify by symbol name
        return self._classify_by_symbol(target_symbol)

    def _classify_by_file(self, file_path: str) -> DependencyType:
        """
        Classify dependency based on file path.

        Args:
            file_path: Absolute path to the file

        Returns:
            Classification
        """
        try:
            path = Path(file_path).resolve()

            # Check if it's under project root
            try:
                path.relative_to(self.project_root)
                is_under_root = True
            except ValueError:
                is_under_root = False

            # If not under project root, it's external or stdlib
            if not is_under_root:
                # Check if it's in stdlib
                for stdlib_path in self._stdlib_paths:
                    try:
                        path.relative_to(stdlib_path)
                        return "stdlib"
                    except ValueError:
                        continue
                # Not stdlib, must be external
                return "external"

            # It's under project root - check if it's in third-party directories
            path_str = str(path).lower()
            for indicator in self._third_party_indicators:
                if indicator in path_str:
                    return "external"

            # It's under project root and not in third-party dir = internal
            return "internal"

        except Exception as e:
            logger.debug(f"Error classifying file {file_path}: {e}")
            return "external"  # Conservative default

    def _classify_by_symbol(self, symbol_name: str) -> DependencyType:
        """
        Classify dependency based on symbol name (fallback when no file path).

        Uses heuristics to determine if a module is stdlib or external.

        Args:
            symbol_name: Symbol name (e.g., "os.path.join", "requests.get")

        Returns:
            Classification
        """
        # Extract module name from symbol (first part before dot)
        module_name = symbol_name.split('.')[0]

        # Check if it's a known stdlib module
        if self._is_stdlib_module(module_name):
            return "stdlib"

        # Check if it's a common third-party package
        if self._is_known_external_module(module_name):
            return "external"

        # If we can't determine, assume external (conservative)
        # This prevents accidental editing of unknown third-party code
        return "external"

    def _is_stdlib_module(self, module_name: str) -> bool:
        """
        Check if a module is part of Python's standard library.

        Args:
            module_name: Module name (e.g., "os", "json")

        Returns:
            True if module is in stdlib
        """
        # Common Python stdlib modules (not exhaustive, but covers most cases)
        stdlib_modules = {
            # Built-in modules
            '__future__', '__main__', '_thread', 'abc', 'aifc', 'argparse',
            'array', 'ast', 'asynchat', 'asyncio', 'asyncore', 'atexit',
            'audioop', 'base64', 'bdb', 'binascii', 'binhex', 'bisect',
            'builtins', 'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath',
            'cmd', 'code', 'codecs', 'codeop', 'collections', 'colorsys',
            'compileall', 'concurrent', 'configparser', 'contextlib', 'contextvars',
            'copy', 'copyreg', 'cProfile', 'crypt', 'csv', 'ctypes', 'curses',
            'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib', 'dis',
            'distutils', 'doctest', 'email', 'encodings', 'enum', 'errno',
            'faulthandler', 'fcntl', 'filecmp', 'fileinput', 'fnmatch',
            'formatter', 'fractions', 'ftplib', 'functools', 'gc', 'getopt',
            'getpass', 'gettext', 'glob', 'graphlib', 'grp', 'gzip', 'hashlib',
            'heapq', 'hmac', 'html', 'http', 'idlelib', 'imaplib', 'imghdr',
            'imp', 'importlib', 'inspect', 'io', 'ipaddress', 'itertools',
            'json', 'keyword', 'lib2to3', 'linecache', 'locale', 'logging',
            'lzma', 'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes',
            'mmap', 'modulefinder', 'msilib', 'msvcrt', 'multiprocessing',
            'netrc', 'nis', 'nntplib', 'numbers', 'operator', 'optparse',
            'os', 'ossaudiodev', 'parser', 'pathlib', 'pdb', 'pickle',
            'pickletools', 'pipes', 'pkgutil', 'platform', 'plistlib', 'poplib',
            'posix', 'posixpath', 'pprint', 'profile', 'pstats', 'pty', 'pwd',
            'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri', 'random', 're',
            'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy', 'sched',
            'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil',
            'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket',
            'socketserver', 'spwd', 'sqlite3', 'ssl', 'stat', 'statistics',
            'string', 'stringprep', 'struct', 'subprocess', 'sunau', 'symbol',
            'symtable', 'sys', 'sysconfig', 'syslog', 'tabnanny', 'tarfile',
            'telnetlib', 'tempfile', 'termios', 'test', 'textwrap', 'threading',
            'time', 'timeit', 'tkinter', 'token', 'tokenize', 'tomllib', 'trace',
            'traceback', 'tracemalloc', 'tty', 'turtle', 'turtledemo', 'types',
            'typing', 'typing_extensions', 'unicodedata', 'unittest', 'urllib',
            'uu', 'uuid', 'venv', 'warnings', 'wave', 'weakref', 'webbrowser',
            'winreg', 'winsound', 'wsgiref', 'xdrlib', 'xml', 'xmlrpc', 'zipapp',
            'zipfile', 'zipimport', 'zlib', 'zoneinfo',
        }

        return module_name in stdlib_modules

    def _is_known_external_module(self, module_name: str) -> bool:
        """
        Check if a module is a well-known third-party package.

        Args:
            module_name: Module name

        Returns:
            True if module is a known third-party package
        """
        # Common third-party packages (not exhaustive)
        external_modules = {
            # Popular packages
            'numpy', 'pandas', 'scipy', 'matplotlib', 'sklearn', 'scikit',
            'tensorflow', 'torch', 'keras', 'django', 'flask', 'fastapi',
            'requests', 'aiohttp', 'httpx', 'beautifulsoup4', 'bs4', 'lxml',
            'sqlalchemy', 'alembic', 'pymongo', 'redis', 'celery', 'pytest',
            'click', 'typer', 'pydantic', 'attrs', 'dataclass', 'marshmallow',
            'boto3', 'botocore', 'stripe', 'twilio', 'sendgrid', 'mailgun',
            'jinja2', 'mako', 'pillow', 'opencv', 'cv2', 'pyyaml', 'toml',
            'black', 'flake8', 'mypy', 'pylint', 'isort', 'poetry', 'pipenv',
            'setuptools', 'wheel', 'pip', 'virtualenv', 'tox', 'nox',
            'cryptography', 'jwt', 'passlib', 'bcrypt', 'argon2',
            'networkx', 'graph', 'plotly', 'seaborn', 'dash', 'streamlit',
            'asyncpg', 'psycopg2', 'mysql', 'pymysql', 'elasticsearch',
            'prometheus', 'grafana', 'sentry', 'raven', 'bugsnag',
            'rich', 'colorama', 'termcolor', 'tabulate', 'prettytable',
        }

        return module_name.lower() in external_modules

    def _get_stdlib_paths(self) -> set[Path]:
        """
        Get paths to Python's standard library.

        Returns:
            Set of Path objects pointing to stdlib directories
        """
        stdlib_paths = set()

        try:
            # Get stdlib path from sysconfig
            stdlib = sysconfig.get_path('stdlib')
            if stdlib:
                stdlib_paths.add(Path(stdlib).resolve())

            # Get platstdlib path (platform-specific stdlib)
            platstdlib = sysconfig.get_path('platstdlib')
            if platstdlib:
                stdlib_paths.add(Path(platstdlib).resolve())

            # Also check sys.prefix paths
            prefix = Path(sys.prefix)
            stdlib_paths.add(prefix / 'lib')
            stdlib_paths.add(prefix / 'lib64')

        except Exception as e:
            logger.debug(f"Error getting stdlib paths: {e}")

        return stdlib_paths

    def get_marker(self, dep_type: DependencyType) -> str:
        """
        Get the visual marker for a dependency type.

        Args:
            dep_type: Dependency classification

        Returns:
            Marker string (e.g., "📦external", "🏠internal", "📦stdlib")
        """
        markers = {
            "internal": "🏠internal",
            "external": "📦external",
            "stdlib": "📦stdlib",
        }
        return markers.get(dep_type, "❓unknown")

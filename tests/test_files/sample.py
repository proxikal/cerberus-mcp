# This is a sample Python file for testing the parser.
import math
from collections import defaultdict

class MyClass:
    """A sample class."""
    def __init__(self, name):
        self.name = name

    def greet(self):
        """A sample method."""
        print(f"Hello, {self.name}")
        top_level_function(1, 2)

def top_level_function(arg1, arg2):
    """A top-level function."""
    return math.sqrt(arg1) + arg2

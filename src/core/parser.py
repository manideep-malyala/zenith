"""Python AST parser module.

Parses source code into an abstract syntax tree (AST) with graceful error handling.
"""

import ast


class PythonParser:
    """Parses a Python source file into an AST handling syntax errors gracefully."""

    def parse_file(self, file_path: str) -> ast.AST | None:
        """Parses a Python file from disk into an AST node.

        Args:
            file_path: Absolute or relative path to the Python source file.

        Returns:
            Optional[ast.AST]: Root AST node if successfully parsed, None on SyntaxError
                or read error.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
            return ast.parse(source, filename=file_path)
        except (SyntaxError, Exception):
            return None

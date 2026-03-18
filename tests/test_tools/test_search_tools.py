"""Test search tools (glob and grep)."""


import pytest

from simple_agent.tools.search_tools import glob_files, grep_content


@pytest.mark.security
class TestGlobFiles:
    """Test glob_files function."""

    def test_glob_py_files(self, temp_workspace):
        """Test finding Python files."""
        # Create some test files
        (temp_workspace / "test.py").write_text("print('hello')")
        (temp_workspace / "test.txt").write_text("hello")
        (temp_workspace / "subdir").mkdir()
        (temp_workspace / "subdir" / "nested.py").write_text("# nested")

        result = glob_files("*.py", str(temp_workspace))
        assert "test.py" in result
        assert "subdir" not in result  # *.py doesn't match nested

    def test_glob_recursive(self, temp_workspace):
        """Test recursive glob pattern."""
        (temp_workspace / "test.py").write_text("print('hello')")
        (temp_workspace / "subdir").mkdir()
        (temp_workspace / "subdir" / "nested.py").write_text("# nested")

        result = glob_files("**/*.py", str(temp_workspace))
        assert "test.py" in result
        assert "subdir/nested.py" in result or "subdir\\nested.py" in result

    def test_glob_no_matches(self, temp_workspace):
        """Test glob with no matches."""
        result = glob_files("*.nonexistent", str(temp_workspace))
        assert "No files found" in result

    def test_glob_all_files(self, temp_workspace):
        """Test finding all files."""
        (temp_workspace / "a.txt").write_text("a")
        (temp_workspace / "b.py").write_text("b")

        result = glob_files("*", str(temp_workspace))
        assert "a.txt" in result
        assert "b.py" in result


@pytest.mark.security
class TestGrepContent:
    """Test grep_content function."""

    def test_grep_simple_pattern(self, temp_workspace):
        """Test simple pattern matching."""
        test_file = temp_workspace / "test.py"
        test_file.write_text("""
def hello():
    print('hello world')
    return 'hello'
""")

        result = grep_content("hello", str(temp_workspace), "*.py")
        assert "test.py" in result
        assert "def hello():" in result or "print('hello world')" in result

    def test_grep_with_file_pattern(self, temp_workspace):
        """Test grep with file pattern filter."""
        (temp_workspace / "test.py").write_text("import os")
        (temp_workspace / "test.txt").write_text("import os")

        result = grep_content("import", str(temp_workspace), "*.py")
        assert "test.py" in result
        # Should not match .txt files

    def test_grep_ignore_case(self, temp_workspace):
        """Test grep with case insensitive matching."""
        test_file = temp_workspace / "test.py"
        test_file.write_text("Hello World")

        result = grep_content("hello", str(temp_workspace), ignore_case=True)
        assert "test.py" in result

    def test_grep_regex_pattern(self, temp_workspace):
        """Test grep with regex pattern."""
        test_file = temp_workspace / "test.py"
        test_file.write_text("""
def test_func():
    pass
def another_func():
    pass
""")

        result = grep_content(r"def \w+_func\(\)", str(temp_workspace), "*.py")
        assert "test_func" in result
        assert "another_func" in result

    def test_grep_no_matches(self, temp_workspace):
        """Test grep with no matches."""
        test_file = temp_workspace / "test.py"
        test_file.write_text("print('hello')")

        result = grep_content("nonexistent_pattern", str(temp_workspace))
        assert "No matches found" in result

    def test_grep_line_numbers(self, temp_workspace):
        """Test that grep includes line numbers."""
        test_file = temp_workspace / "test.py"
        test_file.write_text("line 1\nhello world\nline 3")

        result = grep_content("hello", str(temp_workspace), "*.py")
        assert ":2:" in result or "test.py:2" in result

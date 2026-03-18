"""Test file operation tools."""


import pytest

from simple_agent.tools.file_tools import edit_file, read_file, write_file


@pytest.mark.security
class TestReadFile:
    """Test file reading functionality."""

    def test_read_simple_file(self, sample_files, mock_settings):
        """Test reading a simple text file."""
        result = read_file(str(sample_files["test.txt"]))
        assert "Hello, World!" in result

    def test_read_python_file(self, sample_files):
        """Test reading a Python file."""
        result = read_file(str(sample_files["test.py"]))
        assert "print('Hello')" in result

    def test_read_multiline_file(self, sample_files):
        """Test reading a multi-line file."""
        result = read_file(str(sample_files["multiline.txt"]))
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_read_empty_file(self, sample_files):
        """Test reading an empty file."""
        result = read_file(str(sample_files["empty.txt"]))
        assert result == ""

    def test_read_unicode_file(self, sample_files):
        """Test reading a file with Unicode content."""
        result = read_file(str(sample_files["chinese.txt"]))
        assert "你好，世界！" in result

    def test_read_with_limit(self, sample_files):
        """Test reading with line limit."""
        result = read_file(str(sample_files["multiline.txt"]), limit=2)
        assert "Line 1" in result
        assert "Line 2" in result
        assert "more" in result  # Should mention more lines exist

    def test_read_nonexistent_file(self, temp_workspace):
        """Test reading a file that doesn't exist."""
        result = read_file(str(temp_workspace / "nonexistent.txt"))
        assert "Error" in result or "not found" in result.lower()

    def test_output_size_limit(self, temp_workspace):
        """Test that large file output is truncated."""
        # Create a file larger than 50000 characters
        large_content = "x" * 60000
        large_file = temp_workspace / "large.txt"
        large_file.write_text(large_content)

        result = read_file(str(large_file))
        assert len(result) <= 50000


@pytest.mark.security
class TestWriteFile:
    """Test file writing functionality."""

    def test_write_new_file(self, temp_workspace):
        """Test writing a new file."""
        path = temp_workspace / "new.txt"
        result = write_file(str(path), "New content")

        assert "success" in result.lower() or "wrote" in result.lower()
        assert path.exists()
        assert path.read_text(encoding='utf-8') == "New content"

    def test_write_existing_file(self, sample_files):
        """Test overwriting an existing file."""
        path = sample_files["test.txt"]

        result = write_file(str(path), "Overwritten content")

        assert "success" in result.lower() or "wrote" in result.lower()
        assert path.read_text(encoding='utf-8') == "Overwritten content"

    def test_write_unicode_content(self, temp_workspace):
        """Test writing Unicode content."""
        path = temp_workspace / "unicode.txt"
        content = "Hello 世界 🌍"

        result = write_file(str(path), content)

        assert path.exists()
        assert path.read_text(encoding='utf-8') == content

    def test_write_creates_directories(self, temp_workspace):
        """Test that write_file creates parent directories."""
        path = temp_workspace / "subdir" / "nested" / "file.txt"
        result = write_file(str(path), "Content")

        assert path.exists()
        assert path.parent.is_dir()
        assert path.read_text(encoding='utf-8') == "Content"

    def test_write_empty_content(self, temp_workspace):
        """Test writing empty content."""
        path = temp_workspace / "empty.txt"
        result = write_file(str(path), "")

        assert path.exists()
        assert path.read_text(encoding='utf-8') == ""

    def test_write_large_content(self, temp_workspace):
        """Test writing large content."""
        path = temp_workspace / "large.txt"
        large_content = "x" * 100000

        result = write_file(str(path), large_content)

        assert path.exists()
        assert len(path.read_text(encoding='utf-8')) == 100000


@pytest.mark.security
class TestEditFile:
    """Test file editing functionality."""

    def test_edit_file_success(self, sample_files):
        """Test successful file edit."""
        path = sample_files["test.txt"]

        result = edit_file(str(path), "Hello, World!", "Goodbye, World!")

        assert "success" in result.lower() or "edited" in result.lower()
        new_content = path.read_text(encoding='utf-8')
        assert "Goodbye, World!" in new_content
        assert "Hello, World!" not in new_content

    def test_edit_file_old_text_not_found(self, sample_files):
        """Test edit when old text doesn't exist."""
        path = sample_files["test.txt"]

        result = edit_file(str(path), "Nonexistent text", "New text")

        assert "not found" in result.lower() or "error" in result.lower()

    def test_edit_file_multiline_replacement(self, sample_files):
        """Test multiline text replacement."""
        path = sample_files["multiline.txt"]

        result = edit_file(
            str(path),
            "Line 1\nLine 2",
            "New Line 1\nNew Line 2"
        )

        new_content = path.read_text(encoding='utf-8')
        assert "New Line 1" in new_content
        assert "New Line 2" in new_content

    def test_edit_file_partial_match(self, sample_files):
        """Test edit with partial text match."""
        path = sample_files["test.txt"]

        result = edit_file(str(path), "Hello", "Hi")

        new_content = path.read_text(encoding='utf-8')
        assert "Hi, World!" in new_content

    def test_edit_file_unicode(self, sample_files):
        """Test editing file with Unicode content."""
        path = sample_files["chinese.txt"]

        result = edit_file(str(path), "你好", "您好")

        new_content = path.read_text(encoding='utf-8')
        assert "您好" in new_content
        assert "你好" not in new_content

    def test_edit_file_multiple_occurrences(self, sample_files):
        """Test that only first occurrence is replaced."""
        path = sample_files["multiline.txt"]

        result = edit_file(str(path), "Line", "Row")

        new_content = path.read_text(encoding='utf-8')
        # Only first "Line" should be replaced
        assert new_content.count("Row") >= 1


@pytest.mark.security
class TestFileToolsSecurity:
    """Test security aspects of file tools."""

    def test_path_traversal_prevention(self):
        """Test that path traversal is prevented."""
        # Try to read a file outside workspace
        result = read_file("../../../etc/passwd")
        assert "Error" in result or "escapes" in result.lower()

    def test_write_outside_workspace_prevention(self):
        """Test that writing outside workspace is prevented."""
        result = write_file("../../../etc/malicious", "content")
        assert "Error" in result or "escapes" in result.lower()

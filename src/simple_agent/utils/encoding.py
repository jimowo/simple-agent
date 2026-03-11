"""Encoding utilities for handling text across different platforms.

This module provides utilities for proper text encoding handling,
especially important for Windows environments where encoding issues
are common with GBK/cp936 vs UTF-8.
"""

import locale
import sys
from typing import Optional


def get_system_encoding() -> str:
    """Get the system's preferred encoding.

    Returns:
        System encoding string (e.g., 'utf-8', 'gbk', 'cp936')
    """
    try:
        # Try to get the system's preferred encoding
        encoding = locale.getpreferredencoding(False)
        if encoding:
            return encoding
    except Exception:
        pass

    # Fallback to filesystem encoding
    try:
        encoding = locale.getencoding()
        if encoding:
            return encoding
    except Exception:
        pass

    # Last resort: UTF-8
    return 'utf-8'


def get_console_encoding() -> str:
    """Get the console/terminal encoding.

    Returns:
        Console encoding string
    """
    if sys.platform == 'win32':
        try:
            import ctypes
            import ctypes.wintypes

            # Get console output code page
            code_page = ctypes.windll.kernel32.GetConsoleOutputCP()
            if code_page:
                # Convert code page to encoding name
                encoding_map = {
                    936: 'gbk',
                    950: 'gbk',
                    65001: 'utf-8',
                    1200: 'utf-8',
                    1201: 'utf-8',
                    1252: 'cp1252',
                }
                return encoding_map.get(code_page, f'cp{code_page}')
        except Exception:
            pass

    return get_system_encoding()


def safe_print(text: str, end: str = '\n', file=None) -> None:
    """Print text with proper encoding handling.

    This function handles encoding issues that occur when printing
    text containing non-ASCII characters on Windows.

    Args:
        text: Text to print
        end: String to append after the text
        file: File object to write to (defaults to sys.stdout)
    """
    if file is None:
        file = sys.stdout

    # Try direct print first
    try:
        print(text, end=end, file=file)
        return
    except UnicodeEncodeError:
        pass  # Continue to fallback methods

    console_encoding = get_console_encoding()

    # Fallback: encode for the console
    try:
        encoded = text.encode(console_encoding, errors='replace').decode(console_encoding)
        print(encoded, end=end, file=file)
        return
    except Exception:
        pass  # Continue to last resort

    # Last resort: replace problematic characters
    safe_text = text.encode('ascii', errors='replace').decode('ascii')
    print(safe_text, end=end, file=file)


def safe_input(prompt: str) -> str:
    """Get user input with proper encoding handling.

    Args:
        prompt: Prompt to display

    Returns:
        User input string
    """
    safe_print(prompt, end='')
    return sys.stdin.readline().rstrip('\n')


def decode_output(data: bytes, encodings: Optional[list] = None) -> str:
    """Decode bytes to string with multiple encoding fallbacks.

    Args:
        data: Bytes to decode
        encodings: Optional list of encodings to try (in order)

    Returns:
        Decoded string

    Raises:
        ValueError: If unable to decode with any encoding
    """
    if encodings is None:
        encodings = ['utf-8', 'gbk', 'cp936', 'cp1252', 'latin1', 'ascii']

    for encoding in encodings:
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue

    # If all encodings fail, use replacement
    return data.decode('utf-8', errors='replace')

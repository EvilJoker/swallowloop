"""字符串工具模块测试"""

import pytest

from swallowloop.utils import count_words, is_palindrome, reverse


class TestReverse:
    """reverse 函数测试"""

    def test_reverse_simple_string(self):
        """反转简单字符串"""
        assert reverse("hello") == "olleh"

    def test_reverse_empty_string(self):
        """反转空字符串"""
        assert reverse("") == ""

    def test_reverse_single_char(self):
        """反转单字符"""
        assert reverse("a") == "a"

    def test_reverse_with_spaces(self):
        """反转包含空格的字符串"""
        assert reverse("hello world") == "dlrow olleh"

    def test_reverse_unicode(self):
        """反转 Unicode 字符串"""
        assert reverse("你好世界") == "界世好你"


class TestIsPalindrome:
    """is_palindrome 函数测试"""

    def test_simple_palindrome(self):
        """简单回文"""
        assert is_palindrome("racecar") is True

    def test_not_palindrome(self):
        """非回文"""
        assert is_palindrome("hello") is False

    def test_palindrome_with_spaces(self):
        """包含空格的回文"""
        assert is_palindrome("A man a plan a canal Panama") is True

    def test_palindrome_case_insensitive(self):
        """大小写不敏感"""
        assert is_palindrome("RaceCar") is True

    def test_palindrome_with_punctuation(self):
        """包含标点符号的回文"""
        assert is_palindrome("A man, a plan, a canal: Panama") is True

    def test_empty_string_palindrome(self):
        """空字符串是回文"""
        assert is_palindrome("") is True

    def test_single_char_palindrome(self):
        """单字符是回文"""
        assert is_palindrome("a") is True

    def test_numbers_palindrome(self):
        """数字回文"""
        assert is_palindrome("12321") is True


class TestCountWords:
    """count_words 函数测试"""

    def test_simple_sentence(self):
        """简单句子单词数"""
        assert count_words("hello world") == 2

    def test_single_word(self):
        """单个单词"""
        assert count_words("hello") == 1

    def test_empty_string(self):
        """空字符串"""
        assert count_words("") == 0

    def test_only_spaces(self):
        """仅包含空格"""
        assert count_words("   ") == 0

    def test_multiple_spaces(self):
        """多个连续空格"""
        assert count_words("hello   world") == 2

    def test_leading_trailing_spaces(self):
        """前后有空格"""
        assert count_words("  hello world  ") == 2

    def test_with_tabs_and_newlines(self):
        """包含制表符和换行符"""
        assert count_words("hello\tworld\ntest") == 3

    def test_unicode_words(self):
        """Unicode 字符"""
        assert count_words("你好 世界") == 2

"""列表工具函数测试"""

import pytest

from swallowloop.utils import flatten, unique, chunk


class TestFlatten:
    """flatten 函数测试"""

    def test_flatten_nested_list(self):
        """测试扁平化嵌套列表"""
        result = list(flatten([[1, 2], [3, 4], [5]]))
        assert result == [1, 2, 3, 4, 5]

    def test_flatten_empty_nested_list(self):
        """测试包含空子列表的情况"""
        result = list(flatten([[1, 2], [], [3]]))
        assert result == [1, 2, 3]

    def test_flatten_all_empty(self):
        """测试全部为空的情况"""
        result = list(flatten([[], [], []]))
        assert result == []

    def test_flatten_single_element(self):
        """测试单个元素"""
        result = list(flatten([[1]]))
        assert result == [1]

    def test_flatten_strings(self):
        """测试字符串列表"""
        result = list(flatten([["a", "b"], ["c"]]))
        assert result == ["a", "b", "c"]

    def test_flatten_tuple_input(self):
        """测试元组输入"""
        result = list(flatten(((1, 2), (3, 4))))
        assert result == [1, 2, 3, 4]


class TestUnique:
    """unique 函数测试"""

    def test_unique_basic(self):
        """测试基本去重"""
        result = unique([1, 2, 2, 3, 1])
        assert result == [1, 2, 3]

    def test_unique_all_same(self):
        """测试全部相同的元素"""
        result = unique([1, 1, 1, 1])
        assert result == [1]

    def test_unique_empty_list(self):
        """测试空列表"""
        result = unique([])
        assert result == []

    def test_unique_preserve_order(self):
        """测试保持原始顺序"""
        result = unique([3, 1, 2, 1, 3, 4])
        assert result == [3, 1, 2, 4]

    def test_unique_strings(self):
        """测试字符串去重"""
        result = unique(["a", "b", "a", "c", "b"])
        assert result == ["a", "b", "c"]

    def test_unique_no_duplicates(self):
        """测试无重复元素"""
        result = unique([1, 2, 3])
        assert result == [1, 2, 3]

    def test_unique_tuple_input(self):
        """测试元组输入"""
        result = unique((1, 2, 1, 3))
        assert result == [1, 2, 3]


class TestChunk:
    """chunk 函数测试"""

    def test_chunk_even_split(self):
        """测试均匀分割"""
        result = list(chunk([1, 2, 3, 4, 5, 6], 2))
        assert result == [[1, 2], [3, 4], [5, 6]]

    def test_chunk_uneven_split(self):
        """测试不均匀分割"""
        result = list(chunk([1, 2, 3, 4, 5], 2))
        assert result == [[1, 2], [3, 4], [5]]

    def test_chunk_empty_list(self):
        """测试空列表"""
        result = list(chunk([], 3))
        assert result == []

    def test_chunk_size_larger_than_list(self):
        """测试块大小大于列表长度"""
        result = list(chunk([1, 2], 5))
        assert result == [[1, 2]]

    def test_chunk_size_equals_list_length(self):
        """测试块大小等于列表长度"""
        result = list(chunk([1, 2, 3], 3))
        assert result == [[1, 2, 3]]

    def test_chunk_size_one(self):
        """测试块大小为 1"""
        result = list(chunk([1, 2, 3], 1))
        assert result == [[1], [2], [3]]

    def test_chunk_invalid_size_zero(self):
        """测试无效的块大小 - 0"""
        with pytest.raises(ValueError, match="chunk size must be positive"):
            list(chunk([1, 2, 3], 0))

    def test_chunk_invalid_size_negative(self):
        """测试无效的块大小 - 负数"""
        with pytest.raises(ValueError, match="chunk size must be positive"):
            list(chunk([1, 2, 3], -1))

    def test_chunk_strings(self):
        """测试字符串列表分块"""
        result = list(chunk(["a", "b", "c", "d"], 2))
        assert result == [["a", "b"], ["c", "d"]]

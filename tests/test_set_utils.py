"""集合工具模块测试"""

import pytest

from swallowloop.utils import union_all, intersect_all, difference


class TestUnionAll:
    """union_all 函数测试"""

    def test_union_multiple_sets(self):
        """多个集合并集"""
        result = union_all([{1, 2}, {2, 3}, {4}])
        assert result == {1, 2, 3, 4}

    def test_union_empty_iterable(self):
        """空迭代器返回空集合"""
        result = union_all([])
        assert result == set()

    def test_union_single_set(self):
        """单个集合"""
        result = union_all([{1, 2, 3}])
        assert result == {1, 2, 3}

    def test_union_with_empty_set(self):
        """包含空集合"""
        result = union_all([{1, 2}, set(), {3}])
        assert result == {1, 2, 3}

    def test_union_all_empty(self):
        """全部是空集合"""
        result = union_all([set(), set(), set()])
        assert result == set()

    def test_union_strings(self):
        """字符串集合"""
        result = union_all([{"a", "b"}, {"b", "c"}])
        assert result == {"a", "b", "c"}


class TestIntersectAll:
    """intersect_all 函数测试"""

    def test_intersect_multiple_sets(self):
        """多个集合交集"""
        result = intersect_all([{1, 2, 3}, {2, 3, 4}, {2, 5}])
        assert result == {2}

    def test_intersect_empty_iterable(self):
        """空迭代器返回空集合"""
        result = intersect_all([])
        assert result == set()

    def test_intersect_single_set(self):
        """单个集合返回自身"""
        result = intersect_all([{1, 2, 3}])
        assert result == {1, 2, 3}

    def test_intersect_no_common(self):
        """无公共元素"""
        result = intersect_all([{1, 2}, {3, 4}, {5}])
        assert result == set()

    def test_intersect_with_empty_set(self):
        """包含空集合"""
        result = intersect_all([{1, 2}, set(), {1}])
        assert result == set()

    def test_intersect_strings(self):
        """字符串集合"""
        result = intersect_all([{"a", "b", "c"}, {"b", "c", "d"}, {"b", "e"}])
        assert result == {"b"}


class TestDifference:
    """difference 函数测试"""

    def test_difference_multiple_sets(self):
        """多个集合差集"""
        result = difference({1, 2, 3, 4}, [{2, 3}, {4}])
        assert result == {1}

    def test_difference_empty_others(self):
        """空其他集合"""
        result = difference({1, 2, 3}, [])
        assert result == {1, 2, 3}

    def test_difference_all_removed(self):
        """全部元素被移除"""
        result = difference({1, 2}, [{1, 2}, {3}])
        assert result == set()

    def test_difference_no_overlap(self):
        """无重叠"""
        result = difference({1, 2, 3}, [{4, 5}, {6}])
        assert result == {1, 2, 3}

    def test_difference_with_empty_set(self):
        """包含空集合"""
        result = difference({1, 2, 3}, [set(), {2}])
        assert result == {1, 3}

    def test_difference_strings(self):
        """字符串集合"""
        result = difference({"a", "b", "c", "d"}, [{"b"}, {"c"}])
        assert result == {"a", "d"}

    def test_difference_empty_first(self):
        """第一个集合为空"""
        result = difference(set(), [{1, 2}])
        assert result == set()

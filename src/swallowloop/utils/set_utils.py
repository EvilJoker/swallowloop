"""集合工具模块

提供集合操作的实用函数
"""

from typing import Iterable, TypeVar

T = TypeVar("T")


def union_all(sets: Iterable[set[T]]) -> set[T]:
    """
    计算多个集合的并集

    Args:
        sets: 集合的可迭代对象

    Returns:
        所有集合的并集

    Examples:
        >>> union_all([{1, 2}, {2, 3}, {4}])
        {1, 2, 3, 4}
        >>> union_all([])
        set()
    """
    result: set[T] = set()
    for s in sets:
        result |= s
    return result


def intersect_all(sets: Iterable[set[T]]) -> set[T]:
    """
    计算多个集合的交集

    Args:
        sets: 集合的可迭代对象

    Returns:
        所有集合的交集，如果为空则返回空集合

    Examples:
        >>> intersect_all([{1, 2, 3}, {2, 3, 4}, {2, 5}])
        {2}
        >>> intersect_all([])
        set()
        >>> intersect_all([{1, 2}])
        {1, 2}
    """
    sets_list = list(sets)
    if not sets_list:
        return set()

    result: set[T] = sets_list[0].copy()
    for s in sets_list[1:]:
        result &= s
    return result


def difference(first: set[T], others: Iterable[set[T]]) -> set[T]:
    """
    计算第一个集合与其他集合的差集

    Args:
        first: 第一个集合
        others: 其他集合的可迭代对象

    Returns:
        first 中存在但其他集合中不存在的元素

    Examples:
        >>> difference({1, 2, 3, 4}, [{2, 3}, {4}])
        {1}
        >>> difference({1, 2}, [])
        {1, 2}
    """
    result: set[T] = first.copy()
    for s in others:
        result -= s
    return result

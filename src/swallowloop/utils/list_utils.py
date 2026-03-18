"""列表工具函数"""

from typing import TypeVar, Iterable, Generator

T = TypeVar("T")


def flatten(lst: Iterable[Iterable[T]]) -> Generator[T, None, None]:
    """
    扁平化嵌套列表
    
    Args:
        lst: 嵌套的可迭代对象
        
    Yields:
        扁平化后的元素
        
    Example:
        >>> list(flatten([[1, 2], [3, 4]]))
        [1, 2, 3, 4]
    """
    for item in lst:
        yield from item


def unique(lst: Iterable[T]) -> list[T]:
    """
    去重，保持原始顺序
    
    Args:
        lst: 可迭代对象
        
    Returns:
        去重后的列表，保持首次出现的顺序
        
    Example:
        >>> unique([1, 2, 2, 3, 1])
        [1, 2, 3]
    """
    seen: set[T] = set()
    result: list[T] = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def chunk(lst: list[T], size: int) -> Generator[list[T], None, None]:
    """
    将列表分块
    
    Args:
        lst: 要分块的列表
        size: 每块的大小
        
    Yields:
        分块后的子列表
        
    Raises:
        ValueError: 当 size <= 0 时
        
    Example:
        >>> list(chunk([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]
    """
    if size <= 0:
        raise ValueError(f"chunk size must be positive, got {size}")
    
    for i in range(0, len(lst), size):
        yield lst[i : i + size]

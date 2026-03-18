"""字典工具函数

提供字典的深度访问、设置和扁平化操作。
"""

from typing import Any


def deep_get(d: dict[str, Any], keys: str | list[str], default: Any = None) -> Any:
    """
    深度获取字典值
    
    支持点分隔的键路径或键列表访问嵌套字典。
    
    Args:
        d: 目标字典
        keys: 键路径，可以是点分隔字符串（如 "a.b.c"）或键列表（如 ["a", "b", "c"]）
        default: 键不存在时返回的默认值
    
    Returns:
        找到的值，或默认值
    
    Examples:
        >>> data = {"a": {"b": {"c": 1}}}
        >>> deep_get(data, "a.b.c")
        1
        >>> deep_get(data, ["a", "b", "c"])
        1
        >>> deep_get(data, "a.b.x", default=0)
        0
    """
    if isinstance(keys, str):
        keys = keys.split(".")
    
    result = d
    for key in keys:
        if not isinstance(result, dict) or key not in result:
            return default
        result = result[key]
    return result


def deep_set(d: dict[str, Any], keys: str | list[str], value: Any) -> dict[str, Any]:
    """
    深度设置字典值
    
    在嵌套字典中设置指定路径的值，自动创建不存在的中间字典。
    
    Args:
        d: 目标字典
        keys: 键路径，可以是点分隔字符串或键列表
        value: 要设置的值
    
    Returns:
        修改后的字典（原地修改，返回引用便于链式调用）
    
    Examples:
        >>> data = {}
        >>> deep_set(data, "a.b.c", 1)
        {'a': {'b': {'c': 1}}}
        >>> data
        {'a': {'b': {'c': 1}}}
        >>> deep_set(data, ["a", "b", "d"], 2)
        {'a': {'b': {'c': 1, 'd': 2}}}
    """
    if isinstance(keys, str):
        keys = keys.split(".")
    
    current = d
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        elif not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value
    return d


def flatten_dict(
    d: dict[str, Any], 
    parent_key: str = "", 
    sep: str = "."
) -> dict[str, Any]:
    """
    扁平化嵌套字典
    
    将多层嵌套字典转换为单层字典，键使用分隔符连接。
    
    Args:
        d: 要扁平化的字典
        parent_key: 父键前缀（递归使用）
        sep: 键分隔符，默认为 "."
    
    Returns:
        扁平化后的字典
    
    Examples:
        >>> flatten_dict({"a": {"b": {"c": 1}}})
        {'a.b.c': 1}
        >>> flatten_dict({"a": 1, "b": {"c": 2}})
        {'a': 1, 'b.c': 2}
        >>> flatten_dict({"a": {"b": 1}}, sep="_")
        {'a_b': 1}
    """
    items: list[tuple[str, Any]] = []
    
    for key, value in d.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, sep).items())
        else:
            items.append((new_key, value))
    
    return dict(items)

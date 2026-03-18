"""简单计算器模块

提供基本的数学运算功能。
"""

from typing import Union


Number = Union[int, float]


def add(a: Number, b: Number) -> Number:
    """
    加法运算
    
    Args:
        a: 第一个操作数
        b: 第二个操作数
    
    Returns:
        两数之和
    """
    return a + b


def subtract(a: Number, b: Number) -> Number:
    """
    减法运算
    
    Args:
        a: 被减数
        b: 减数
    
    Returns:
        两数之差
    """
    return a - b


def multiply(a: Number, b: Number) -> Number:
    """
    乘法运算
    
    Args:
        a: 第一个操作数
        b: 第二个操作数
    
    Returns:
        两数之积
    """
    return a * b


def divide(a: Number, b: Number) -> float:
    """
    除法运算
    
    Args:
        a: 被除数
        b: 除数
    
    Returns:
        两数之商
    
    Raises:
        ZeroDivisionError: 当除数为零时抛出
    """
    if b == 0:
        raise ZeroDivisionError("除数不能为零")
    return a / b

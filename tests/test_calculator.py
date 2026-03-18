"""
计算器模块测试

测试基本数学运算功能。
"""

import pytest

from swallowloop.utils.calculator import add, subtract, multiply, divide


class TestAdd:
    """加法测试"""

    def test_add_integers(self):
        """整数加法"""
        assert add(1, 2) == 3
        assert add(-1, 1) == 0
        assert add(0, 0) == 0

    def test_add_floats(self):
        """浮点数加法"""
        assert add(1.5, 2.5) == 4.0
        assert add(-0.1, 0.1) == pytest.approx(0.0)

    def test_add_mixed_types(self):
        """混合类型加法"""
        assert add(1, 2.5) == 3.5


class TestSubtract:
    """减法测试"""

    def test_subtract_integers(self):
        """整数减法"""
        assert subtract(5, 3) == 2
        assert subtract(1, 1) == 0
        assert subtract(0, 5) == -5

    def test_subtract_floats(self):
        """浮点数减法"""
        assert subtract(5.5, 2.5) == 3.0
        assert subtract(0.3, 0.1) == pytest.approx(0.2)


class TestMultiply:
    """乘法测试"""

    def test_multiply_integers(self):
        """整数乘法"""
        assert multiply(3, 4) == 12
        assert multiply(-2, 3) == -6
        assert multiply(0, 100) == 0

    def test_multiply_floats(self):
        """浮点数乘法"""
        assert multiply(2.5, 2) == 5.0
        assert multiply(0.1, 0.2) == pytest.approx(0.02)


class TestDivide:
    """除法测试"""

    def test_divide_integers(self):
        """整数除法"""
        assert divide(10, 2) == 5.0
        assert divide(7, 2) == 3.5

    def test_divide_floats(self):
        """浮点数除法"""
        assert divide(5.0, 2.0) == 2.5
        assert divide(1.0, 3.0) == pytest.approx(0.333333, rel=1e-5)

    def test_divide_by_zero(self):
        """除零异常"""
        with pytest.raises(ZeroDivisionError):
            divide(10, 0)

    def test_divide_negative(self):
        """负数除法"""
        assert divide(-10, 2) == -5.0
        assert divide(10, -2) == -5.0
        assert divide(-10, -2) == 5.0

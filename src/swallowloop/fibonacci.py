"""斐波那契数列算法模块

提供多种斐波那契数列计算方法。
"""


def fibonacci_recursive(n: int) -> int:
    """递归方式计算斐波那契数列第 n 项。

    时间复杂度: O(2^n)
    空间复杂度: O(n)

    Args:
        n: 项数（从 0 开始）

    Returns:
        斐波那契数列第 n 项的值

    Raises:
        ValueError: 当 n 为负数时
    """
    if n < 0:
        raise ValueError("n 必须为非负整数")
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


def fibonacci_iterative(n: int) -> int:
    """迭代方式计算斐波那契数列第 n 项。

    时间复杂度: O(n)
    空间复杂度: O(1)

    Args:
        n: 项数（从 0 开始）

    Returns:
        斐波那契数列第 n 项的值

    Raises:
        ValueError: 当 n 为负数时
    """
    if n < 0:
        raise ValueError("n 必须为非负整数")
    if n <= 1:
        return n

    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr
    return curr


def fibonacci_generator(n: int) -> list[int]:
    """生成斐波那契数列前 n 项。

    Args:
        n: 要生成的项数

    Returns:
        包含前 n 项斐波那契数的列表

    Raises:
        ValueError: 当 n 为负数时
    """
    if n < 0:
        raise ValueError("n 必须为非负整数")
    if n == 0:
        return []

    result = [0]
    if n == 1:
        return result

    result.append(1)
    for i in range(2, n):
        result.append(result[i - 1] + result[i - 2])

    return result


def fibonacci_memoized(n: int, memo: dict[int, int] | None = None) -> int:
    """带记忆化的递归方式计算斐波那契数列第 n 项。

    时间复杂度: O(n)
    空间复杂度: O(n)

    Args:
        n: 项数（从 0 开始）
        memo: 记忆化字典（内部使用）

    Returns:
        斐波那契数列第 n 项的值

    Raises:
        ValueError: 当 n 为负数时
    """
    if n < 0:
        raise ValueError("n 必须为非负整数")

    if memo is None:
        memo = {0: 0, 1: 1}

    if n in memo:
        return memo[n]

    memo[n] = fibonacci_memoized(n - 1, memo) + fibonacci_memoized(n - 2, memo)
    return memo[n]


if __name__ == "__main__":
    # 示例用法
    print("斐波那契数列前 10 项:")
    print(fibonacci_generator(10))

    print("\n第 10 项的值:")
    print(f"递归: {fibonacci_recursive(10)}")
    print(f"迭代: {fibonacci_iterative(10)}")
    print(f"记忆化: {fibonacci_memoized(10)}")

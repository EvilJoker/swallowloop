"""字符串工具模块"""


def reverse(s: str) -> str:
    """反转字符串
    
    Args:
        s: 要反转的字符串
        
    Returns:
        反转后的字符串
    """
    return s[::-1]


def is_palindrome(s: str) -> bool:
    """判断字符串是否为回文
    
    忽略大小写，仅检查字母和数字字符
    
    Args:
        s: 要检查的字符串
        
    Returns:
        如果是回文返回 True，否则返回 False
    """
    cleaned = "".join(c.lower() for c in s if c.isalnum())
    return cleaned == cleaned[::-1]


def count_words(s: str) -> int:
    """统计字符串中的单词数
    
    按空白字符分割统计单词数量
    
    Args:
        s: 要统计的字符串
        
    Returns:
        单词数量
    """
    if not s or not s.strip():
        return 0
    return len(s.split())

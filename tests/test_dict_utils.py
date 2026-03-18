"""字典工具函数测试"""

import pytest

from swallowloop.utils import deep_get, deep_set, flatten_dict
from swallowloop.utils.dict_utils import deep_get, deep_set, flatten_dict


class TestDeepGet:
    """deep_get 函数测试"""
    
    def test_simple_key(self):
        """测试简单键访问"""
        data = {"a": 1, "b": 2}
        assert deep_get(data, "a") == 1
        assert deep_get(data, "b") == 2
    
    def test_nested_keys_with_string(self):
        """测试点分隔字符串访问嵌套字典"""
        data = {"a": {"b": {"c": 1}}}
        assert deep_get(data, "a.b.c") == 1
        assert deep_get(data, "a.b") == {"c": 1}
    
    def test_nested_keys_with_list(self):
        """测试键列表访问嵌套字典"""
        data = {"a": {"b": {"c": 1}}}
        assert deep_get(data, ["a", "b", "c"]) == 1
        assert deep_get(data, ["a", "b"]) == {"c": 1}
    
    def test_missing_key_returns_default(self):
        """测试键不存在返回默认值"""
        data = {"a": {"b": 1}}
        assert deep_get(data, "a.c", default=0) == 0
        assert deep_get(data, "x.y.z", default="not found") == "not found"
        assert deep_get(data, "a.b.c") is None
    
    def test_non_dict_value(self):
        """测试非字典值路径访问"""
        data = {"a": 1}
        assert deep_get(data, "a.b") is None
        assert deep_get(data, "a.b", default=0) == 0
    
    def test_empty_dict(self):
        """测试空字典"""
        assert deep_get({}, "a.b.c") is None
        assert deep_get({}, "a.b.c", default=0) == 0
    
    def test_empty_keys(self):
        """测试空键路径"""
        data = {"a": 1}
        assert deep_get(data, "") == None


class TestDeepSet:
    """deep_set 函数测试"""
    
    def test_set_simple_key(self):
        """测试设置简单键"""
        data = {}
        result = deep_set(data, "a", 1)
        assert data["a"] == 1
        assert result is data  # 返回同一对象
    
    def test_set_nested_keys_with_string(self):
        """测试点分隔字符串设置嵌套值"""
        data = {}
        deep_set(data, "a.b.c", 1)
        assert data == {"a": {"b": {"c": 1}}}
    
    def test_set_nested_keys_with_list(self):
        """测试键列表设置嵌套值"""
        data = {}
        deep_set(data, ["a", "b", "c"], 1)
        assert data == {"a": {"b": {"c": 1}}}
    
    def test_create_intermediate_dicts(self):
        """测试自动创建中间字典"""
        data = {}
        deep_set(data, "a.b.c.d.e", 1)
        assert data["a"]["b"]["c"]["d"]["e"] == 1
    
    def test_overwrite_value(self):
        """测试覆盖已有值"""
        data = {"a": {"b": 1}}
        deep_set(data, "a.b", 2)
        assert data["a"]["b"] == 2
    
    def test_overwrite_non_dict_with_dict(self):
        """测试覆盖非字典值为字典"""
        data = {"a": 1}
        deep_set(data, "a.b", 2)
        assert data == {"a": {"b": 2}}
    
    def test_chain_calls(self):
        """测试链式调用"""
        data = {}
        deep_set(deep_set(deep_set(data, "a", {}), "a.b", 1), "c", 2)
        assert data == {"a": {"b": 1}, "c": 2}


class TestFlattenDict:
    """flatten_dict 函数测试"""
    
    def test_simple_dict(self):
        """测试简单字典不变"""
        data = {"a": 1, "b": 2}
        assert flatten_dict(data) == {"a": 1, "b": 2}
    
    def test_nested_dict(self):
        """测试嵌套字典扁平化"""
        data = {"a": {"b": {"c": 1}}}
        assert flatten_dict(data) == {"a.b.c": 1}
    
    def test_mixed_dict(self):
        """测试混合层级字典"""
        data = {"a": 1, "b": {"c": 2}, "d": {"e": {"f": 3}}}
        assert flatten_dict(data) == {"a": 1, "b.c": 2, "d.e.f": 3}
    
    def test_custom_separator(self):
        """测试自定义分隔符"""
        data = {"a": {"b": {"c": 1}}}
        assert flatten_dict(data, sep="_") == {"a_b_c": 1}
        assert flatten_dict(data, sep="/") == {"a/b/c": 1}
    
    def test_empty_dict(self):
        """测试空字典"""
        assert flatten_dict({}) == {}
    
    def test_deeply_nested(self):
        """测试深层嵌套"""
        data = {"a": {"b": {"c": {"d": {"e": 1}}}}}
        assert flatten_dict(data) == {"a.b.c.d.e": 1}
    
    def test_multiple_keys_at_same_level(self):
        """测试同一层级多个键"""
        data = {"a": {"b": 1, "c": 2}, "d": {"e": 3, "f": 4}}
        result = flatten_dict(data)
        assert result == {"a.b": 1, "a.c": 2, "d.e": 3, "d.f": 4}


class TestIntegration:
    """集成测试：deep_get, deep_set, flatten_dict 配合使用"""
    
    def test_set_and_get(self):
        """测试设置后获取"""
        data = {}
        deep_set(data, "config.database.host", "localhost")
        deep_set(data, "config.database.port", 5432)
        
        assert deep_get(data, "config.database.host") == "localhost"
        assert deep_get(data, "config.database.port") == 5432
    
    def test_flatten_and_reconstruct(self):
        """测试扁平化后部分重建"""
        original = {"a": {"b": 1, "c": {"d": 2}}}
        flat = flatten_dict(original)
        
        # 重建
        reconstructed = {}
        for key, value in flat.items():
            deep_set(reconstructed, key, value)
        
        assert reconstructed == original

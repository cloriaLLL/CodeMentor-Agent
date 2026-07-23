"""CodeMentor Agent - External problem fetcher service.

Fetches real programming problems from public repositories:
- GitHub repos with interview/LeetCode problems
- Parses Markdown descriptions into normalized exercise format
- Caches results in SQLite for offline use
"""
from __future__ import annotations

import json
import re
import urllib.request
from typing import Optional

from app.core.database import get_db
from app.core.logger import get_logger

logger = get_logger(__name__)

# Known public repositories with programming problems
# Using raw GitHub content URLs for reliable access
_PROBLEM_SOURCES = {
    "leetcode": {
        "label": "LeetCode 题目",
        "repos": [
            "https://raw.githubusercontent.com/doocs/leetcode/main/solution/0000-0099/",
        ],
    },
    "interview": {
        "label": "面试题目",
        "repos": [
            "https://api.github.com/repos/kdn251/interviews/contents/README.md",
        ],
    },
}

# Built-in problem set for offline use
_BUILTIN_PROBLEMS = [
    {
        "source": "builtin",
        "source_id": "twosum",
        "title": "两数之和",
        "difficulty": "Easy",
        "description": """给定一个整数数组 `nums` 和一个整数目标值 `target`，请你在该数组中找出和为目标值的那两个整数，并返回它们的数组下标。

你可以假设每种输入只会对应一个答案。但是，数组中同一个元素在答案里不能重复出现。

**示例**：
```
输入：nums = [2,7,11,15], target = 9
输出：[0,1]
解释：因为 nums[0] + nums[1] == 9 ，返回 [0, 1]
```""",
        "starter_code": """def two_sum(nums: list[int], target: int) -> list[int]:
    # 请补全代码
    pass
""",
        "test_cases": """from solution import two_sum

def test_two_sum_basic():
    assert two_sum([2, 7, 11, 15], 9) == [0, 1]

def test_two_sum_reverse():
    assert two_sum([3, 2, 4], 6) == [1, 2]

def test_two_sum_same_value():
    assert two_sum([3, 3], 6) == [0, 1]

def test_two_sum_negative():
    assert two_sum([-1, -2, -3, -4, -5], -8) == [2, 4]
""",
        "tags": "array,hash-table,算法",
    },
    {
        "source": "builtin",
        "source_id": "reverse_string",
        "title": "反转字符串",
        "difficulty": "Easy",
        "description": """编写一个函数，其作用是将输入的字符串反转过来。输入字符串以字符数组 `s` 的形式给出。

不要给另外的数组分配额外的空间，你必须**原地修改输入数组**、使用 O(1) 的额外空间解决这个问题。

**示例**：
```
输入：s = ["h","e","l","l","o"]
输出：["o","l","l","e","h"]
```""",
        "starter_code": """def reverse_string(s: list[str]) -> None:
    # 请补全代码
    pass
""",
        "test_cases": """from solution import reverse_string

def test_reverse_basic():
    s = ["h", "e", "l", "l", "o"]
    reverse_string(s)
    assert s == ["o", "l", "l", "e", "h"]

def test_reverse_empty():
    s = []
    reverse_string(s)
    assert s == []

def test_reverse_single():
    s = ["a"]
    reverse_string(s)
    assert s == ["a"]
""",
        "tags": "string,two-pointers,算法",
    },
    {
        "source": "builtin",
        "source_id": "valid_parentheses",
        "title": "有效的括号",
        "difficulty": "Easy",
        "description": """给定一个只包括 `(`、`)`、`{`、`}`、`[`、`]` 的字符串 `s`，判断字符串是否有效。

有效字符串需满足：
1. 左括号必须用相同类型的右括号闭合。
2. 左括号必须以正确的顺序闭合。
3. 每个右括号都有一个对应的相同类型的左括号。

**示例**：
```
输入：s = "()[]{}"
输出：true

输入：s = "([)]"
输出：false
```""",
        "starter_code": """def is_valid(s: str) -> bool:
    # 请补全代码
    pass
""",
        "test_cases": """from solution import is_valid

def test_valid_simple():
    assert is_valid("()") == True

def test_valid_multiple():
    assert is_valid("()[]{}") == True

def test_invalid_nested():
    assert is_valid("([)]") == False

def test_valid_nested():
    assert is_valid("{[]}") == True

def test_empty():
    assert is_valid("") == True

def test_single_open():
    assert is_valid("(") == False
""",
        "tags": "string,stack,算法",
    },
    {
        "source": "builtin",
        "source_id": "decorator_logging",
        "title": "实现日志装饰器",
        "difficulty": "Medium",
        "description": """请实现一个 `@log_calls` 装饰器，在函数调用时自动记录日志信息。

**要求**：
1. 记录函数名、参数、返回值
2. 记录执行耗时（毫秒级）
3. 使用 `functools.wraps` 保留元信息
4. 日志格式：`[LOG] func_name(args) -> result (X.XXms)`""",
        "starter_code": """from functools import wraps
import time

def log_calls(func):
    # 请补全代码
    pass
""",
        "test_cases": """from solution import log_calls

def test_log_basic():
    @log_calls
    def add(a, b):
        return a + b
    assert add(1, 2) == 3

def test_log_preserves_metadata():
    @log_calls
    def my_func():
        \"\"\"My docstring.\"\"\"
        return 'x'
    assert my_func.__name__ == 'my_func'
    assert my_func.__doc__ == 'My docstring.'

def test_log_with_kwargs():
    @log_calls
    def greet(name, greeting="Hello"):
        return f"{greeting}, {name}"
    assert greet("World") == "Hello, World"
    assert greet("World", greeting="Hi") == "Hi, World"
""",
        "tags": "decorator,python,高级特性",
    },
    {
        "source": "builtin",
        "source_id": "lru_cache",
        "title": "实现 LRU 缓存",
        "difficulty": "Medium",
        "description": """设计并实现一个 LRU（最近最少使用）缓存机制。

实现 `LRUCache` 类：
- `LRUCache(capacity)` - 以正整数作为容量 capacity 初始化 LRU 缓存
- `get(key)` - 如果关键字 key 存在于缓存中，则返回关键字的值，否则返回 -1
- `put(key, value)` - 如果关键字已经存在，则变更其数据值；如果不存在，则向缓存中插入该组。如果插入操作导致关键字数量超过 capacity，则应该逐出最久未使用的关键字。

**要求**：`get` 和 `put` 的时间复杂度均为 O(1)。""",
        "starter_code": """class LRUCache:
    def __init__(self, capacity: int):
        # 请补全代码
        pass

    def get(self, key: int) -> int:
        pass

    def put(self, key: int, value: int) -> None:
        pass
""",
        "test_cases": """from solution import LRUCache

def test_lru_basic():
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1
    cache.put(3, 3)  # evicts key 2
    assert cache.get(2) == -1
    cache.put(4, 4)  # evicts key 1
    assert cache.get(1) == -1
    assert cache.get(3) == 3
    assert cache.get(4) == 4

def test_lru_update_existing():
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.put(1, 10)  # update
    cache.put(3, 3)   # evicts key 2
    assert cache.get(2) == -1
    assert cache.get(1) == 10

def test_lru_get_updates_order():
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.get(1)       # makes 1 recently used
    cache.put(3, 3)    # evicts key 2
    assert cache.get(2) == -1
    assert cache.get(1) == 1
""",
        "tags": "design,hash-table,linked-list,数据结构",
    },
    {
        "source": "builtin",
        "source_id": "merge_sorted_lists",
        "title": "合并两个有序链表",
        "difficulty": "Easy",
        "description": """将两个升序链表合并为一个新的**升序**链表并返回。新链表是通过拼接给定的两个链表的所有节点组成的。

**示例**：
```
输入：l1 = [1,2,4], l2 = [1,3,4]
输出：[1,1,2,3,4,4]
```""",
        "starter_code": """class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def merge_two_lists(l1: ListNode, l2: ListNode) -> ListNode:
    # 请补全代码
    pass
""",
        "test_cases": """from solution import ListNode, merge_two_lists

def list_to_array(head):
    result = []
    while head:
        result.append(head.val)
        head = head.next
    return result

def array_to_list(arr):
    if not arr:
        return None
    head = ListNode(arr[0])
    cur = head
    for v in arr[1:]:
        cur.next = ListNode(v)
        cur = cur.next
    return head

def test_merge_basic():
    l1 = array_to_list([1, 2, 4])
    l2 = array_to_list([1, 3, 4])
    result = merge_two_lists(l1, l2)
    assert list_to_array(result) == [1, 1, 2, 3, 4, 4]

def test_merge_one_empty():
    l1 = array_to_list([])
    l2 = array_to_list([1, 2, 3])
    result = merge_two_lists(l1, l2)
    assert list_to_array(result) == [1, 2, 3]

def test_merge_both_empty():
    result = merge_two_lists(None, None)
    assert result is None
""",
        "tags": "linked-list,recursion,数据结构",
    },
]


class ProblemFetcherService:
    """Service for fetching and caching external programming problems."""

    def __init__(self) -> None:
        self.db = get_db()

    def load_builtin_problems(self) -> int:
        """Load built-in problems into cache. Returns count loaded."""
        count = 0
        for problem in _BUILTIN_PROBLEMS:
            try:
                self.db.execute(
                    """INSERT OR IGNORE INTO problem_cache
                       (source, source_id, title, difficulty, description, starter_code, test_cases, tags)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        problem["source"],
                        problem["source_id"],
                        problem["title"],
                        problem["difficulty"],
                        problem["description"],
                        problem["starter_code"],
                        problem["test_cases"],
                        problem["tags"],
                    ),
                )
                count += 1
            except Exception as e:
                logger.warning("failed_to_cache_problem", source_id=problem["source_id"], error=str(e))
        logger.info("builtin_problems_loaded", count=count)
        return count

    def get_problems(
        self,
        source: Optional[str] = None,
        tag: Optional[str] = None,
        difficulty: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """Get cached problems with optional filtering."""
        conditions = []
        params: list = []

        if source:
            conditions.append("source = ?")
            params.append(source)
        if tag:
            conditions.append("tags LIKE ?")
            params.append(f"%{tag}%")
        if difficulty:
            conditions.append("difficulty = ?")
            params.append(difficulty)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"SELECT * FROM problem_cache{where_clause} ORDER BY fetched_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.db.query_all(sql, tuple(params))
        return [dict(r) for r in rows]

    def get_problem_by_id(self, problem_id: int) -> Optional[dict]:
        """Get a single problem by its cache ID."""
        row = self.db.query_one("SELECT * FROM problem_cache WHERE id = ?", (problem_id,))
        return dict(row) if row else None

    def get_tags(self) -> list[str]:
        """Get all unique tags from cached problems."""
        rows = self.db.query_all("SELECT DISTINCT tags FROM problem_cache WHERE tags IS NOT NULL")
        tags = set()
        for row in rows:
            for tag in (row["tags"] or "").split(","):
                tag = tag.strip()
                if tag:
                    tags.add(tag)
        return sorted(tags)

    def get_sources(self) -> list[dict]:
        """Get all problem sources."""
        return [
            {"source": k, "label": v["label"]}
            for k, v in _PROBLEM_SOURCES.items()
        ] + [{"source": "builtin", "label": "内置题库"}]

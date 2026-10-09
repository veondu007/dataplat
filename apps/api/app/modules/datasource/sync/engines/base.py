"""引擎接口：推断 schema / 读取行 / 准备目标表。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EngineColumn:
    name: str
    source_type: str  # 源类型字符串（如 "varchar(64)"）


@dataclass
class EngineTable:
    database_name: str
    name: str
    comment: str | None = None


class BaseEngine(ABC):
    """数据源引擎抽象。实现类持有连接参数，提供：
    - test_conn：连通性
    - list_tables：源表列表
    - columns：表列定义
    - read_rows：按批读取行（生成器，产出 list[list]）
    - prepare_target / engine 相关由 sync 流程编排。
    """

    @abstractmethod
    def test_conn(self) -> dict:
        """返回 {ok, latency_ms, message}。"""

    @abstractmethod
    def list_tables(self) -> list[EngineTable]:
        """列出可同步的表。"""

    @abstractmethod
    def columns(self, table: str) -> list[EngineColumn]:
        """返回表列定义。"""

    @abstractmethod
    def read_rows(self, table: str, batch_size: int = 1000):
        """按批产出数据行（list[list]）。xlsx 用 sheet 名作 table。"""
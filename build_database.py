'''
建立 / 同步数据库表结构

根据 `DB_SCHEMAS` 中的 `TableSchema` 与磁盘上 SQLite 对比：
- 表不存在：执行 `CREATE TABLE IF NOT EXISTS`（与原先一致）
- 表已存在：对比列名（大小写不敏感）
  - schema 有、库中无：`ALTER TABLE ... ADD COLUMN`
  - 库中有、schema 无：若该列在库中为 **主键组成部分**（`PRAGMA table_info` 的 `pk` 非 0），只打 **warning** 并跳过；否则交互询问 `y/N` 后执行 `DROP COLUMN`（需 SQLite 3.35+）

说明：不处理「列改名」；主键变更需手工迁表。本脚本适合本地手动执行。
'''
from __future__ import annotations

import os
import sqlite3
from typing import Dict, List, Set, Tuple

from utils import add_root_path
add_root_path()

from utils import TableSchema
from utils import get_logger
logger = get_logger(name='build_database')

# 常量
from db import DB_DIR
from schema.trade_calendar import TRADE_CALENDAR_SCHEMAS_LIST
from schema.security_info import SECURITY_INFO_SCHEMAS_LIST
from schema.minutely_trade_data import MINUTELY_TRADE_DATA_SCHEMAS_LIST
from schema.daily_trade_data import DAILY_TRADE_DATA_SCHEMAS_LIST
from schema.adjustment_factor import ADJUSTMENT_FACTOR_SCHEMAS_LIST
DB_SCHEMAS = {
    'trade_calendar.db': TRADE_CALENDAR_SCHEMAS_LIST,
    'security_info.db': SECURITY_INFO_SCHEMAS_LIST,
    'minutely_trade_data.db': MINUTELY_TRADE_DATA_SCHEMAS_LIST,
    'daily_trade_data.db': DAILY_TRADE_DATA_SCHEMAS_LIST,
    'adjustment_factor.db': ADJUSTMENT_FACTOR_SCHEMAS_LIST
} # 表结构列表


def _sqlite_supports_drop_column() -> bool:
    parts = sqlite3.sqlite_version.split('.')
    major, minor = int(parts[0]), int(parts[1])
    return (major, minor) >= (3, 35)


def _quoted_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _get_ddl_by_schema(schema: TableSchema) -> str:
    pk = schema.primary_key
    pk_set = set(pk)

    if len(pk) == 1:
        pk_name = pk[0]
        col_defs = []
        for field in schema.schema:
            if field.name == pk_name:
                col_defs.append(f"{field.name} {field.sql_type} PRIMARY KEY")
            else:
                col_defs.append(f"{field.name} {field.sql_type}")
        body = ', '.join(col_defs)
    elif len(pk) > 1:
        col_defs = []
        for field in schema.schema:
            if field.name in pk_set:
                col_defs.append(f"{field.name} {field.sql_type} NOT NULL")
            else:
                col_defs.append(f"{field.name} {field.sql_type}")
        body = ', '.join(col_defs) + f", PRIMARY KEY ({', '.join(pk)})"
    else:
        body = ', '.join(f'{f.name} {f.sql_type}' for f in schema.schema)

    return f'CREATE TABLE IF NOT EXISTS {schema.table_name} ({body})'


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cur.fetchone() is not None


def _pragma_column_meta(
    conn: sqlite3.Connection, table_name: str
) -> Dict[str, Tuple[str, bool]]:
    '''
    列名（维持库中原始大小写） -> (声明类型, 是否为主键的组成部分)
    PRAGMA table_info 最后一列 pk：0 表示非主键，非 0 表示参与主键（含复合主键中的顺序）。
    '''
    cur = conn.execute(f'PRAGMA table_info({_quoted_ident(table_name)})')
    out: Dict[str, Tuple[str, bool]] = {}
    for row in cur.fetchall():
        # cid, name, type, notnull, dflt_value, pk
        cname = row[1]
        ctype = row[2] or ''
        is_pk_part = int(row[5] or 0) != 0
        out[cname] = (ctype, is_pk_part)
    return out


def _schema_column_lower_map(schema: TableSchema) -> Dict[str, Tuple[str, str]]:
    '''小写列名 -> (schema 中的真实列名, sql_type)'''
    m: Dict[str, Tuple[str, str]] = {}
    for field in schema.schema:
        key = field.name.lower()
        if key in m:
            raise ValueError(
                f'表 {schema.table_name} schema 列名大小写冲突: {m[key][0]} / {field.name}'
            )
        m[key] = (field.name, field.sql_type)
    return m


def _diff_columns(
    schema_map: Dict[str, Tuple[str, str]],
    db_cols: Dict[str, str],
) -> Tuple[List[Tuple[str, str]], List[str]]:
    '''
    返回 (待 ADD 的 (name, sql_type) 列表按 schema 顺序隐含在调用方),
    待用 DROP 的实际库列名列表（保留库中大小写）
    '''
    db_lower_to_actual: Dict[str, str] = {k.lower(): k for k in db_cols}
    schema_lowers: Set[str] = set(schema_map.keys())
    db_lowers: Set[str] = set(db_lower_to_actual.keys())

    to_add_low = schema_lowers - db_lowers
    to_drop_low = db_lowers - schema_lowers

    to_add_ordered: List[Tuple[str, str]] = []
    for low in sorted(to_add_low):
        name, sql_type = schema_map[low]
        to_add_ordered.append((name, sql_type))

    to_drop_actual: List[str] = []
    for low in sorted(to_drop_low):
        to_drop_actual.append(db_lower_to_actual[low])

    return to_add_ordered, to_drop_actual


def _prompt_drop_column(table_name: str, column: str) -> bool:
    tip = (
        f'表 {_quoted_ident(table_name)} 的列 {_quoted_ident(column)} '
        f'已不在 schema 中，是否执行 DROP COLUMN？[y/N]: '
    )
    try:
        ans = input(tip).strip().lower()
    except EOFError:
        logger.warning('无法读取输入，跳过 DROP %s.%s', table_name, column)
        return False
    return ans == 'y'


def sync_table(conn: sqlite3.Connection, schema: TableSchema) -> None:
    if not _table_exists(conn, schema.table_name):
        ddl = _get_ddl_by_schema(schema)
        logger.info('创建表 %s', schema.table_name)
        conn.execute(ddl)
        conn.commit()
        return

    db_meta = _pragma_column_meta(conn, schema.table_name)
    db_cols = {name: meta[0] for name, meta in db_meta.items()}
    schema_map = _schema_column_lower_map(schema)
    to_add, to_drop = _diff_columns(schema_map, db_cols)

    for col_name, sql_type in to_add:
        sql = (
            f'ALTER TABLE {_quoted_ident(schema.table_name)} '
            f'ADD COLUMN {_quoted_ident(col_name)} {sql_type}'
        )
        logger.info('ADD COLUMN: %s', sql)
        conn.execute(sql)

    if to_drop and not _sqlite_supports_drop_column():
        logger.error(
            '当前 SQLite 版本 %s 不支持 DROP COLUMN（需 3.35+），以下列未删除: %s',
            sqlite3.sqlite_version,
            to_drop,
        )
        conn.commit()
        return

    for col_name in to_drop:
        _ctype, is_pk_part = db_meta[col_name]
        if is_pk_part:
            logger.warning(
                '跳过 DROP 主键列 %s.%s（SQLite 不允许；请手工建新表/迁数据后再删旧列）',
                schema.table_name,
                col_name,
            )
            continue
        if not _prompt_drop_column(schema.table_name, col_name):
            logger.info('保留列 %s.%s', schema.table_name, col_name)
            continue
        sql = f'ALTER TABLE {_quoted_ident(schema.table_name)} DROP COLUMN {_quoted_ident(col_name)}'
        logger.info('DROP COLUMN: %s', sql)
        conn.execute(sql)

    conn.commit()


def main() -> None:
    os.makedirs(DB_DIR, exist_ok=True)
    for db in DB_SCHEMAS:
        path = os.path.join(DB_DIR, db)
        conn = sqlite3.connect(path)
        try:
            for schema in DB_SCHEMAS[db]:
                if schema.database_name != db:
                    logger.warning(
                        'schema %s 的 database_name=%s 与当前文件 %s 不一致，仍按文件同步',
                        schema.table_name,
                        schema.database_name,
                        db,
                    )
                sync_table(conn, schema)
        finally:
            conn.close()


if __name__ == '__main__':
    main()

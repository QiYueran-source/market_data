"""
校验工具

用于校验处理后得到的 df 和 TableSchema 是否一致。

调用方（如 Provider / Job）捕获异常后在顶层记录日志。  
"""
from __future__ import annotations
from typing import Any, List
import numpy as np
import pandas as pd
from pandas.api.types import (
    is_datetime64_any_dtype,
    is_float_dtype,
    is_integer_dtype,
    is_object_dtype,
)

# 表结构
from utils.schema import TableSchema

# 异常
from exceptions.valid_error import (
    FieldNameUnmatchError,
    FieldTypeUnmatchError,
    PrimaryKeyUnmatchError,
    PrimaryKeyDuplicateError,
    PrimaryKeyEmptyError,
)

def _is_pk_in_df(df: pd.DataFrame, pk: List[str]) -> bool:
    '''
    判断 df 是否包含 pk 列
    '''
    return all(col in df.columns for col in pk)

def _df_cols_subset_of_schema(df: pd.DataFrame, schema: TableSchema) -> bool:
    '''
    若 df 的列集合是 schema 列名的子集，则返回 True（即 df 不含 schema 未定义的列）。
    '''
    return set(df.columns) <= set(schema.cols)

def _is_dtype_matched_for_series(series: pd.Series, expected_dtype: Any) -> bool:
    """判断 Series 的 dtype 是否与 schema 中 Field.dtype（多为 numpy）兼容。"""
    exp = np.dtype(expected_dtype)

    if np.issubdtype(exp, np.integer):
        return bool(is_integer_dtype(series))
    if np.issubdtype(exp, np.floating):
        return bool(is_float_dtype(series))
    if np.issubdtype(exp, np.datetime64):
        return bool(is_datetime64_any_dtype(series))
    # 文本：object / string / numpy str_
    if exp.kind in ('U', 'S', 'O') or exp == np.dtype(object):
        return bool(is_object_dtype(series) or pd.api.types.is_string_dtype(series))

    # 其它：尽量用 numpy 安全转换判断
    try:
        return np.can_cast(series.dtype, exp, casting='same_kind')
    except (TypeError, ValueError):
        return False

def _is_dtype_matched(df: pd.DataFrame, schema: TableSchema) -> bool:
    '''
    判断 df 中字段类型是否与 schema 中字段类型兼容
    '''
    return all(_is_dtype_matched_for_series(df[col], schema.get_field_by_name(col).dtype) for col in df.columns)

def _is_pk_duplicate(df: pd.DataFrame, schema: TableSchema) -> bool:
    '''
    若主键组合无重复行，返回 True。
    '''
    return not df.duplicated(subset=schema.primary_key).any()

def _is_pk_empty(df: pd.DataFrame, schema: TableSchema) -> bool:
    '''
    若主键列中无任何空值，返回 True。
    '''
    return not df[schema.primary_key].isna().any().any()

def valid(df: pd.DataFrame, schema: TableSchema) -> bool:
    '''
    校验 df 和 schema 是否一致

    一致要求：
    - 0. df 列名唯一（无重复列名）
    - 1. 当 ``primary_key_required`` 为 True 时，df 须包含 schema 全部主键列
    - 2. df 的列必须都在 TableSchema 中定义（不能有额外列）
    - 3. df 的字段类型需与 TableSchema 中对应 Field.dtype 兼容
    - 4. 当 ``primary_key_required`` 为 True 时，主键组合无重复（空 DataFrame 视为通过）
    - 5. 当 ``primary_key_required`` 为 True 时，主键列无空值

    报错：
    - PrimaryKeyUnmatchError: 在要求主键时，df 缺少主键列
    - FieldNameUnmatchError: df 列名重复，或含 schema 未定义的列名
    - FieldTypeUnmatchError: 列 dtype 与 schema 不兼容
    - PrimaryKeyDuplicateError: 主键组合有重复行
    - PrimaryKeyEmptyError: 主键列存在空值
    '''
    if not df.columns.is_unique:
        raise FieldNameUnmatchError('df 中存在重复列名，请检查')

    # 1.df中是否包含全部主键列
    if schema.primary_key_required and not _is_pk_in_df(df, schema.primary_key):
        raise PrimaryKeyUnmatchError(f'df 缺少主键列，请检查')

    # 2.df 列是否为 schema 列名的子集（无多余列）
    if not _df_cols_subset_of_schema(df, schema):
        raise FieldNameUnmatchError(f'df 包含 schema 未定义的列名，请检查')

    # 3.df中字段类型是否与schema中字段类型兼容
    if not _is_dtype_matched(df, schema):
        raise FieldTypeUnmatchError(f'df 中字段类型与 schema 不兼容，请检查')

    # 4.df中主键组合无重复
    if schema.primary_key_required and not _is_pk_duplicate(df, schema):
        raise PrimaryKeyDuplicateError(f'df 中主键组合有重复')

    # 5.df中主键组合无空值
    if schema.primary_key_required and not _is_pk_empty(df, schema):
        raise PrimaryKeyEmptyError(f'df 中主键组合有空值')

    return True
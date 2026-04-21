'''
etf_info表的API接口     
- get_all_etf_info() 获取所有ETF信息  
- get_etf_list() 获取ETF列表  
- get_latest_etf_info() 获取最新ETF信息  
- get_latest_etf_list() 获取最新ETF列表  
- get_etf_info_by_code() 获取指定代码的ETF信息  
- match_etf_info_by_concept() 根据名称匹配ETF信息  
- match_etf_info_by_exchange() 根据交易所匹配ETF信息    
- get_latest_update_date() 获取最新更新日期  
'''
# 库
import datetime as dt
import pandas as pd
from typing import List, Sequence, Literal

# 常量
from db.api.security_info import _security_info_query

DB_NAME = _security_info_query.SECURITY_INFO_DB_NAME
TABLE_NAME = 'etf_info'
_SELECT = _security_info_query.SELECT_ALL_COLS

# etf_info.exchange 存大写市场码，与库中一致
_ALLOWED_ETF_EXCHANGES = frozenset({'SH', 'SZ'})

# 兜底ETF
FALLBACK_ETF_CODE = '888888'

def _fb() -> tuple[str]:
    return (FALLBACK_ETF_CODE,)

def get_all_etf_info() -> pd.DataFrame:
    '''
    获取所有ETF信息

    - 返回
        - pandas.DataFrame: ETF信息表
            - code: str ETF代码
            - name: str ETF名称
            - exchange: str ETF所在交易所
            - last_update_date: str 最后更新日期
    '''
    q = f'SELECT {_SELECT} FROM {TABLE_NAME} WHERE code != ?'
    return _security_info_query.read_sql(q, _fb())

def get_etf_list(with_suffix: bool = False) -> List[str]:
    '''
    获取ETF列表  

    - 参数
        - with_suffix: bool 是否返回带交易所后缀代码（如 513100.SH）
    - 返回
        - List[str]: ETF列表
            - str: ETF代码（默认无后缀；with_suffix=True 时为 code.exchange）
    '''
    q = f'SELECT code, exchange FROM {TABLE_NAME} WHERE code != ?'
    df = _security_info_query.read_sql(q, _fb())
    if not with_suffix:
        return df['code'].astype(str).tolist()
    return [
        f"{str(code)}.{str(exchange).upper()}"
        for code, exchange in zip(df['code'], df['exchange'])
    ]

def get_latest_etf_info() -> pd.DataFrame:
    '''
    获取最新ETF信息  

    判断逻辑：选取last_update_date最新的记录

    - 返回
        - pandas.DataFrame: 最新ETF信息表
            - code: str ETF代码
            - name: str ETF名称
            - exchange: str ETF所在交易所
            - last_update_date: str 最后更新日期
    '''
    q = f'''
    SELECT {_SELECT} FROM {TABLE_NAME}
        WHERE last_update_date = (
            SELECT MAX(last_update_date) FROM {TABLE_NAME}
        )
        AND code != ?
    '''
    return _security_info_query.read_sql(q, _fb())

def get_latest_etf_list(with_suffix: bool = False) -> List[str]:
    '''
    获取最新ETF列表

    - 参数
        - with_suffix: bool 是否返回带交易所后缀代码（如 513100.SH）
    - 返回
        - List[str]: 最新ETF列表
            - str: ETF代码（默认无后缀；with_suffix=True 时为 code.exchange）
    '''
    q = f'''
    SELECT code, exchange FROM {TABLE_NAME}
    WHERE last_update_date = (
        SELECT MAX(last_update_date) FROM {TABLE_NAME}
    )
    AND code != ?
    '''
    df = _security_info_query.read_sql(q, _fb())
    if not with_suffix:
        return df['code'].astype(str).tolist()
    return [
        f"{str(code)}.{str(exchange).upper()}"
        for code, exchange in zip(df['code'], df['exchange'])
    ]


def get_etf_info_by_code(code: str | Sequence[str]) -> pd.DataFrame:
    '''
    获取指定代码的ETF信息

    - 返回
        - pandas.DataFrame: ETF信息表
            - code: str ETF代码
            - name: str ETF名称
            - exchange: str ETF所在交易所
            - last_update_date: str 最后更新日期
    '''
    if not code:
        raise ValueError('code不能为空')
    if isinstance(code, str):
        q = f'SELECT {_SELECT} FROM {TABLE_NAME} WHERE code = ? AND code != ?'
        params: tuple[str, ...] = (code, FALLBACK_ETF_CODE)
        return _security_info_query.read_sql(q, params)
    if isinstance(code, Sequence):
        ph = ','.join(['?'] * len(code))
        q = f'SELECT {_SELECT} FROM {TABLE_NAME} WHERE code IN ({ph}) AND code != ?'
        params = tuple(code) + (FALLBACK_ETF_CODE,)
        return _security_info_query.read_sql(q, params)
    raise TypeError(f'code 类型不支持: {type(code)}')


def _normalize_concept_keywords(concepts: str | Sequence[str]) -> list[str]:
    if isinstance(concepts, str):
        raw = [concepts]
    elif isinstance(concepts, Sequence):
        raw = [str(c) for c in concepts]
    else:
        raise TypeError(f'concepts 类型不支持: {type(concepts)}')
    keywords = [k.strip() for k in raw if k and str(k).strip()]
    if not keywords:
        raise ValueError('concepts不能为空')
    return keywords


def match_etf_info_by_concept(concepts: str | Sequence[str]) -> pd.DataFrame:
    '''
    根据名称（name 列）子串匹配 ETF 信息。

    例如 concepts 为 ['石油', '天然气'] 时，返回 name 中包含「石油」或「天然气」任一的行。

    使用参数化 SQL + instr，避免拼接注入与 LIKE 通配符问题。

    - 返回
        - pandas.DataFrame: ETF信息表
            - code: str ETF代码
            - name: str ETF名称
            - exchange: str ETF所在交易所
            - last_update_date: str 最后更新日期
    '''
    keywords = _normalize_concept_keywords(concepts)
    conds = ' OR '.join(['instr(name, ?) > 0'] * len(keywords))
    q = f'SELECT {_SELECT} FROM {TABLE_NAME} WHERE ({conds}) AND code != ?'
    params = tuple(keywords) + (FALLBACK_ETF_CODE,)
    return _security_info_query.read_sql(q, params)


def _normalize_exchange_values(exchanges: str | Sequence[str]) -> list[str]:
    '''
    规范为库中 exchange 取值：大写 **SH** / **SZ**。
    '''
    if isinstance(exchanges, str):
        raw = [exchanges]
    elif isinstance(exchanges, Sequence):
        raw = [str(e) for e in exchanges]
    else:
        raise TypeError(f'exchanges 类型不支持: {type(exchanges)}')
    canonical: list[str] = []
    for item in raw:
        e = item.strip().upper()
        if not e:
            continue
        if e not in _ALLOWED_ETF_EXCHANGES:
            raise ValueError(
                f'不支持的交易所: {item!r}，仅允许 {sorted(_ALLOWED_ETF_EXCHANGES)}',
            )
        canonical.append(e)
    if not canonical:
        raise ValueError('exchanges不能为空')
    seen: set[str] = set()
    out: list[str] = []
    for x in canonical:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def match_etf_info_by_exchange(
    exchanges: Literal['SH', 'SZ'] | str | Sequence[str],
) -> pd.DataFrame:
    '''
    根据 exchange 列匹配 ETF 信息。

    库中存 **大写** ``SH`` / ``SZ``；入参大小写不敏感，会规范为大写后查询。
    例如 ``['SH', 'SZ']`` 或 ``['sh', 'sz']`` 均合法。

    - 返回
        - pandas.DataFrame: ETF信息表
            - code: str ETF代码
            - name: str ETF名称
            - exchange: str ETF所在交易所
            - last_update_date: str 最后更新日期
    '''
    values = _normalize_exchange_values(exchanges)
    if len(values) == 1:
        q = f'SELECT {_SELECT} FROM {TABLE_NAME} WHERE exchange = ? AND code != ?'
        params = (values[0], FALLBACK_ETF_CODE)
    else:
        placeholders = ','.join(['?'] * len(values))
        q = f'SELECT {_SELECT} FROM {TABLE_NAME} WHERE exchange IN ({placeholders}) AND code != ?'
        params = tuple(values) + (FALLBACK_ETF_CODE,)
    return _security_info_query.read_sql(q, params)


def get_latest_update_date() -> dt.date:
    '''
    获取最新更新日期

    - 返回
        - dt.date: 最新更新日期

    表为空或 MAX(last_update_date) 为 NULL 时抛出 ValueError。
    '''
    raw = _security_info_query.fetch_max_last_update_date(TABLE_NAME)
    if raw is None:
        raise ValueError('etf_info 无有效 last_update_date（表为空或列为 NULL）')
    return dt.datetime.strptime(raw, '%Y-%m-%d').date()

try:
    # Linux expects the latest package version of 3.31.1 (as of p)
    import pysqlite3 as sqlite3
except ModuleNotFoundError:
    # MacOS expects the latest brew version of 3.32.1 (as of 2020-07-10).
    # Windows builds use the official Python 3.7.8 builds and version of 3.31.1.
    import sqlite3 # type: ignore
from typing import Any, List, NamedTuple, Optional, Sequence

from ..constants import DerivationType, KeyInstanceFlag, ScriptType, TxFlags
from ..logs import logs
from .sqlite_support import with_sqlite_connection
from .util import flag_clause, read_rows_by_id


logger = logs.get_logger("db-functions")


class KeyListRow(NamedTuple):
    keyinstance_id: int
    masterkey_id: Optional[int]
    derivation_type: DerivationType
    derivation_data: bytes
    flags: KeyInstanceFlag
    date_updated: int
    tx_hash: Optional[bytes]
    txo_script_type: Optional[ScriptType]
    txo_index: Optional[int]
    txo_value: Optional[int]

class TransactionDeltaSumRow(NamedTuple):
    account_id: int
    total: int


@with_sqlite_connection
def read_account_balance(db: sqlite3.Connection, account_id: int, flags: Optional[int]=None,
        mask: Optional[int]=None) -> TransactionDeltaSumRow:
    query = ("SELECT TXV.account_id, TOTAL(TXV.value), COUNT(DISTINCT TXV.tx_hash) "
        "FROM TransactionValues TXV "
        "{} "
        "WHERE TXV.account_id = ? "
        "{}"
        "GROUP BY TXV.account_id")
    params: List[Any] = [ account_id ]
    clause, extra_params = flag_clause("TX.flags", flags, mask)
    if clause:
        query = query.format("INNER JOIN Transactions TX ON TX.tx_hash=TXV.tx_hash ",
            f" AND {clause} ")
        params.extend(extra_params)
    else:
        query = query.format("", "")
    cursor = db.execute(query, params)
    row = cursor.fetchone()
    cursor.close()
    if row is None:
        return TransactionDeltaSumRow(account_id, 0, 0)
    return TransactionDeltaSumRow(*row)


class HistoryListRow(NamedTuple):
    tx_hash: bytes
    tx_flags: TxFlags
    block_height: Optional[int]
    block_position: Optional[int]
    value_delta: int


@with_sqlite_connection
def read_history_list(db: sqlite3.Connection, account_id: int,
        keyinstance_ids: Optional[Sequence[int]]=None) -> List[HistoryListRow]:
    if keyinstance_ids:
        # Used for the address dialog.
        query = ("SELECT TXV.tx_hash, TX.flags, TX.block_height, TX.block_position, "
                "TOTAL(TD.value), TX.date_added "
            "FROM TransactionValues TXV "
            "INNER JOIN Transactions AS TX ON TX.tx_hash=TXV.tx_hash "
            "WHERE TXV.account_id=? AND TD.keyinstance_id IN ({}) AND "
                f"(T.flags & {TxFlags.STATE_MASK})!=0"
            "GROUP BY TXV.tx_hash")
        return read_rows_by_id(HistoryListRow, db, query, [ account_id ], keyinstance_ids)

    # Used for the history list and export.
    query = ("SELECT TXV.tx_hash, TX.flags, TX.block_height, TX.block_position, "
            "TOTAL(TD.value), TX.date_added "
        "FROM TransactionValues TXV "
        "INNER JOIN Transactions AS TX ON TX.tx_hash=TXV.tx_hash "
        f"WHERE TXV.account_id=? AND (T.flags & {TxFlags.STATE_MASK})!=0"
        "GROUP BY TXV.tx_hash")
    cursor = db.execute(query, [account_id])
    rows = cursor.fetchall()
    cursor.close()
    return [ HistoryListRow(*t) for t in rows ]


@with_sqlite_connection
def read_key_list(db: sqlite3.Connection, account_id: int,
        keyinstance_ids: Optional[Sequence[int]]=None) -> List[KeyListRow]:
    params = [ account_id ]
    if keyinstance_ids is not None:
        query = ("SELECT KI.keyinstance_id, KI.masterkey_id, KI.derivation_type, "
                "KI.derivation_data, KI.flags, KI.date_updated, TXO.tx_hash, TXO.tx_index, "
                "TXO.script_type, TXO.value  "
            "FROM KeyInstances AS KI "
            "LEFT JOIN TransactionOutputs TXO ON TXO.keyinstance_id = TXO.keyinstance_id "
            "WHERE KI.account_id = ? AND KI.keyinstance_id IN ({}) "
            "GROUP BY KI.keyinstance_id")
        return read_rows_by_id(KeyListRow, db, query, [ account_id ], keyinstance_ids)

    query = ("SELECT KI.keyinstance_id, KI.masterkey_id, KI.derivation_type, "
            "KI.derivation_data, KI.flags, KI.date_updated, TXO.tx_hash, TXO.tx_index, "
            "TXO.script_type, TXO.value "
        "FROM KeyInstances AS KI "
        "LEFT JOIN TransactionOutputs TXO ON TXO.keyinstance_id = TXO.keyinstance_id "
        "WHERE KI.account_id = ?")
    cursor = db.execute(query, [account_id])
    rows = cursor.fetchall()
    cursor.close()
    return [ KeyListRow(*t) for t in rows ]


@with_sqlite_connection
def read_paid_requests(db: sqlite3.Connection, account_id: int, keyinstance_ids: Sequence[int]) \
        -> List[int]:
    # TODO(nocheckin) ensure this is filtering out transactions or transaction outputs that
    # are not relevant.
    query = ("SELECT PR.keyinstance_id "
        "FROM PaymentRequests PR "
        "INNER JOIN TransactionOutputs TXO ON TXO.keyinstance_id=PR.keyinstance_id "
        "INNER JOIN AccountTransactions ATX ON ATX.tx_hash=TXO.tx_hash AND ATX.account_id = ?"
        "WHERE PR.keyinstance_id IN ({}) AND (PR.state & {PaymentFlag.UNPAID}) != 0 "
        "GROUP BY PR.keyinstance_id "
        "HAVING PR.value IS NULL OR PR.value <= TOTAL(TXO.value)")
    return read_rows_by_id(int, db, query, [ account_id ], keyinstance_ids)


@with_sqlite_connection
def read_transaction_value(db: sqlite3.Connection, tx_hash: bytes,
        account_id: Optional[int]=None) -> List[TransactionDeltaSumRow]:
    if account_id is None:
        query = ("SELECT account_id, TOTAL(value) "
            "FROM TransactionValues "
            "WHERE tx_hash=? "
            "GROUP BY account_id")
        cursor = db.execute(query, [tx_hash])
    else:
        query = ("SELECT account_id, TOTAL(value) "
            "FROM TransactionValues "
            "WHERE account_id=? AND tx_hash=? "
            "GROUP BY account_id")
        cursor = db.execute(query, [account_id, tx_hash])
    rows = cursor.fetchall()
    cursor.close()
    return [ TransactionDeltaSumRow(*row) for row in rows ]

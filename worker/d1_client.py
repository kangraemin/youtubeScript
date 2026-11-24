"""먹맵 본 데이터(Cloudflare D1 mukmap-db) 클라이언트.

2026-11-25 먹맵은 Supabase를 쓰지 않는다. restaurants / videos / channels / processing_queue / alert_* / push_subs 는
여기로 읽고 쓴다. transcripts 는 youtube-script-web 과 같이 쓰는 표라 아직 Supabase(supabase_client.get_client)에 있다.

낮은 층:  query(sql, params) / batch([(sql, params), ...])   — D1 REST API (POST .../d1/database/{id}/query)
높은 층:  get_d1().table("restaurants").select(...).eq(...).execute()  — supabase-py 와 같은 모양(.data / .count)
          그래서 find_restaurant / upsert_restaurant 같은 기존 도우미가 클라이언트만 바꿔 그대로 돈다.

D1 규칙: jsonb 칸은 JSON 글자, boolean 은 0/1, 시각은 ISO 글자. 쓸 때 dict/list → JSON, bool → 0/1로 바꾸고
읽을 때 JSON 칸·boolean 칸을 되돌린다. REST 한도(5분 1200번)를 지키려고 호출 사이 간격을 두고 429/5xx 는 다시 시도한다.
"""
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

_ENV_LOCAL = Path(__file__).resolve().parent.parent / ".env.local"
DATABASE_ID = "189c0c85-3ca8-41fc-8359-736c276e4408"  # mukmap-db

# menu·price·quote·why는 글자 칸이다. 여기 두면 "[1]" 같은 값이 목록으로 풀려 모양이 바뀐다(11/25 검토)
JSON_COLS = {"detail", "i18n", "extraction_result"}
BOOL_COLS = {"needs_review", "is_visible", "is_ad"}
# 기본키/고유키로 선언된 조합 — 이 조합이면 ON CONFLICT 로, 아니면 UPDATE 후 INSERT-없을 때만 으로 흉내 낸다
UNIQUE_KEYS = {
    "channels": ("id",),
    "alert_subs": ("anon_key", "channel_id"),
    "alert_state": ("channel_id",),
    "alert_near": ("anon_key", "restaurant_id"),
    "alert_near_state": ("anon_key",),
    "push_subs": ("token", "channel_id"),
}
TABLES = {"channels", "restaurants", "videos", "processing_queue",
          "alert_subs", "alert_state", "alert_near", "alert_near_state", "push_subs"}
# 끼워 넣기 select("restaurants(id,name)") 용 관계: (표, 관계이름) → (종류, 열)
RELATIONS = {
    ("videos", "restaurants"): ("one", "restaurant_id"),     # videos.restaurant_id → restaurants.id
    ("restaurants", "videos"): ("many", "restaurant_id"),    # videos.restaurant_id = restaurants.id
}

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_PARAMS = 90          # D1 는 문장당 바인딩 100개까지 — 넘으면 숫자·글자를 문장에 직접 적는다
BATCH_CHUNK = 40         # 한 요청에 담는 문장 수
MIN_INTERVAL = 0.35      # 전체 스레드 합쳐 초당 3번 이하. API 한도(1200/5분)를 꽉 채우면 wrangler·번역 스크립트와 겹쳐 429가 난다(11/25 검토)

_rate_lock = threading.Lock()
_last_call = 0.0


def now_iso() -> str:
    """D1 기본값(strftime '%Y-%m-%dT%H:%M:%fZ')과 같은 모양의 지금 시각 — 글자 비교가 맞도록 이 모양만 쓴다."""
    return to_iso(datetime.now(timezone.utc))


def to_iso(dt) -> str:
    """datetime(시간대 있음) → D1 비교용 UTC ISO 글자."""
    u = dt.astimezone(timezone.utc)
    return u.strftime("%Y-%m-%dT%H:%M:%S.") + f"{u.microsecond // 1000:03d}Z"


class D1Error(RuntimeError):
    pass


def _creds() -> tuple[str, str]:
    load_dotenv(_ENV_LOCAL)  # override=False — 기존 env 우선
    acc, tok = os.environ.get("MUKMAP_CF_ACCOUNT"), os.environ.get("MUKMAP_CF_TOKEN")
    if not acc or not tok:
        raise RuntimeError("D1 자격 증명 없음: MUKMAP_CF_ACCOUNT / MUKMAP_CF_TOKEN 필요")
    return acc, tok


def _throttle() -> None:
    global _last_call
    with _rate_lock:
        wait = _last_call + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def _post(body: dict, tries: int = 6, base_delay: float = 2.0) -> list[dict]:
    acc, tok = _creds()
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/d1/database/{DATABASE_ID}/query"
    for i in range(tries):
        _throttle()
        try:
            r = requests.post(url, headers={"Authorization": f"Bearer {tok}"}, json=body, timeout=60)
        except requests.RequestException:
            if i == tries - 1:
                raise
            time.sleep(base_delay * (2 ** i))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            if i == tries - 1:
                raise D1Error(f"D1 HTTP {r.status_code}")
            time.sleep(float(r.headers.get("Retry-After") or base_delay * (2 ** i)))
            continue
        try:
            data = r.json()
        except ValueError:
            raise D1Error(f"D1 응답이 JSON 아님 (HTTP {r.status_code})")
        if not data.get("success"):
            msgs = "; ".join(str(e.get("message")) for e in data.get("errors") or [])
            if i < tries - 1 and re.search(r"(?i)overloaded|temporar|try again|network|timeout|reset", msgs):
                time.sleep(base_delay * (2 ** i))
                continue
            raise D1Error(f"D1 오류 (HTTP {r.status_code}): {msgs[:500]}")
        return data["result"]
    raise D1Error("D1 재시도 초과")


def _param(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return v


def _lit(v) -> str:
    v = _param(v)
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def query(sql: str, params: list | None = None) -> dict:
    """문장 하나. {"rows": [...], "changes": n, "last_row_id": n}"""
    return batch([(sql, params or [])])[0]


def batch(stmts: list[tuple[str, list]]) -> list[dict]:
    """여러 문장을 한 요청(한 트랜잭션)으로. 결과는 문장 순서대로."""
    out: list[dict] = []
    for i in range(0, len(stmts), BATCH_CHUNK):
        chunk = stmts[i:i + BATCH_CHUNK]
        res = _post({"batch": [{"sql": s, "params": [_param(p) for p in ps]} for s, ps in chunk]})
        for r in res:
            if not r.get("success", True):
                raise D1Error("D1 문장 실패")
            meta = r.get("meta") or {}
            out.append({"rows": r.get("results") or [], "changes": meta.get("changes", 0),
                        "last_row_id": meta.get("last_row_id")})
    return out


def _decode(row: dict) -> dict:
    for k in list(row):
        v = row[k]
        if k in BOOL_COLS and v is not None:
            row[k] = bool(v)
        elif k in JSON_COLS and isinstance(v, str) and v[:1] in ("[", "{"):
            try:
                row[k] = json.loads(v)
            except ValueError:
                pass
    return row


def _ident(name: str) -> str:
    if not _IDENT.match(name):
        raise ValueError(f"잘못된 이름: {name!r}")
    return name


class Result:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


def _split_top(s: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


class Query:
    def __init__(self, table: str):
        if table not in TABLES:
            raise ValueError(f"D1에 없는 표: {table} (transcripts 는 Supabase 클라이언트를 쓴다)")
        self.table = table
        self.op = "select"
        self.cols = "*"
        self.count_mode = None
        self.head = False
        self.where: list[tuple[str, list]] = []
        self.orders: list[str] = []
        self._limit = None
        self._offset = None
        self._single = None   # "single" | "maybe"
        self._rows = None
        self._values = None
        self._conflict = None
        self._neg = False

    # ── 문장 종류 ──
    def select(self, cols="*", count=None, head=False):
        self.op, self.cols, self.count_mode, self.head = "select", cols, count, head
        return self

    def insert(self, values):
        self.op, self._rows = "insert", values if isinstance(values, list) else [values]
        return self

    def upsert(self, values, on_conflict=None):
        self.op, self._rows = "upsert", values if isinstance(values, list) else [values]
        self._conflict = tuple(c.strip() for c in on_conflict.split(",")) if on_conflict else None
        return self

    def update(self, values: dict):
        self.op, self._values = "update", values
        return self

    def delete(self):
        self.op = "delete"
        return self

    # ── 조건 ──
    @property
    def not_(self):
        self._neg = True
        return self

    def _add(self, sql: str, params: list):
        if self._neg:
            sql, self._neg = f"NOT ({sql})", False
        self.where.append((sql, params))
        return self

    def _cmp(self, col, op, val):
        return self._add(f"{_ident(col)} {op} ?", [_param(val)])

    def eq(self, col, val):
        if val is None:
            return self._add(f"{_ident(col)} IS NULL", [])
        return self._cmp(col, "=", val)

    def neq(self, col, val):
        return self._cmp(col, "!=", val)

    def gt(self, col, val):
        return self._cmp(col, ">", val)

    def gte(self, col, val):
        return self._cmp(col, ">=", val)

    def lt(self, col, val):
        return self._cmp(col, "<", val)

    def lte(self, col, val):
        return self._cmp(col, "<=", val)

    def like(self, col, val):
        return self._cmp(col, "LIKE", val)

    ilike = like  # SQLite LIKE 는 영문 대소문자를 가리지 않는다

    def is_(self, col, val):
        if val in ("null", None):
            return self._add(f"{_ident(col)} IS NULL", [])
        return self._add(f"{_ident(col)} IS ?", [_param(val in ("true", True))])

    def in_(self, col, vals):
        vals = list(vals)
        if not vals:
            return self._add("0", [])
        if len(vals) > MAX_PARAMS:
            return self._add(f"{_ident(col)} IN ({','.join(_lit(v) for v in vals)})", [])
        return self._add(f"{_ident(col)} IN ({','.join('?' * len(vals))})", [_param(v) for v in vals])

    # ── 모양 ──
    def order(self, col, desc=False, nullsfirst=None):
        s = f"{_ident(col)} {'DESC' if desc else 'ASC'}"
        if nullsfirst is not None:
            s += " NULLS FIRST" if nullsfirst else " NULLS LAST"
        self.orders.append(s)
        return self

    def limit(self, n):
        self._limit = int(n)
        return self

    def range(self, a, b):
        self._offset, self._limit = int(a), int(b) - int(a) + 1
        return self

    def single(self):
        self._single = "single"
        return self.limit(2)

    def maybe_single(self):
        self._single = "maybe"
        return self.limit(2)

    # ── 실행 ──
    def _where_sql(self):
        if not self.where:
            return "", []
        return " WHERE " + " AND ".join(f"({s})" for s, _ in self.where), [p for _, ps in self.where for p in ps]

    def execute(self) -> Result:
        return getattr(self, f"_x_{self.op}")()

    def _x_select(self) -> Result:
        plain, rels = [], []
        for c in _split_top(self.cols):
            m = re.match(r"^(\w+)\((.*)\)$", c)
            if m:
                rels.append((m.group(1), m.group(2)))
            else:
                plain.append(c if c == "*" else _ident(c))
        # 끼워 넣기에 필요한 연결 열은 같이 가져오고 나중에 뺀다
        extra = []
        for rel, _ in rels:
            kind, col = RELATIONS[(self.table, rel)]
            key = col if kind == "one" else "id"
            if "*" not in plain and key not in plain:
                plain.append(key)
                extra.append(key)
        w, wp = self._where_sql()
        sql = f"SELECT {', '.join(plain) or '*'} FROM {self.table}{w}"
        if self.orders:
            sql += " ORDER BY " + ", ".join(self.orders)
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
            if self._offset:
                sql += f" OFFSET {self._offset}"
        elif self._offset:
            sql += f" LIMIT -1 OFFSET {self._offset}"
        stmts = [(sql, wp)]
        if self.count_mode:
            stmts.append((f"SELECT COUNT(*) AS n FROM {self.table}{w}", wp))
        if self.head:
            stmts = stmts[1:]
        res = batch(stmts)
        count = res[-1]["rows"][0]["n"] if self.count_mode else None
        rows = [] if self.head else [_decode(r) for r in res[0]["rows"]]
        for rel, rcols in rels:
            self._attach(rows, rel, rcols)
        for r in rows:
            for k in extra:
                r.pop(k, None)
        if self._single:
            if len(rows) == 1:
                return Result(rows[0], count)
            if self._single == "maybe" and not rows:
                return Result(None, count)
            raise D1Error(f"single() 결과가 {len(rows)}행")
        return Result(rows, count)

    def _attach(self, rows: list[dict], rel: str, rcols: str):
        kind, col = RELATIONS[(self.table, rel)]
        key = col if kind == "one" else "id"
        keys = sorted({r[key] for r in rows if r.get(key) is not None})
        found: dict = {}
        for i in range(0, len(keys), MAX_PARAMS):
            part = keys[i:i + MAX_PARAMS]
            match = "id" if kind == "one" else col
            want = [c.strip() for c in rcols.split(",")]
            sel = list(dict.fromkeys(want + [match]))
            got = Query(rel).select(",".join(sel)).in_(match, part).execute().data
            for g in got:
                k = g[match]
                if kind == "one":
                    found[k] = {c: g[c] for c in want}
                else:
                    found.setdefault(k, []).append({c: g[c] for c in want})
        for r in rows:
            r[rel] = found.get(r.get(key)) if kind == "one" else found.get(r.get(key), [])

    @staticmethod
    def _cols_vals(row: dict):
        cols = [_ident(c) for c in row]
        return cols, [_param(row[c]) for c in row]

    def _x_insert(self) -> Result:
        stmts = []
        for row in self._rows:
            cols, vals = self._cols_vals(row)
            stmts.append((f"INSERT INTO {self.table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))}) RETURNING *", vals))
        res = batch(stmts)
        return Result([_decode(r) for x in res for r in x["rows"]])

    def _x_upsert(self) -> Result:
        conflict = self._conflict or UNIQUE_KEYS.get(self.table) or ("id",)
        stmts = []
        for row in self._rows:
            cols, vals = self._cols_vals(row)
            rest = [c for c in cols if c not in conflict]
            if tuple(conflict) == UNIQUE_KEYS.get(self.table):
                sets = ", ".join(f"{c}=excluded.{c}" for c in rest)
                action = f"DO UPDATE SET {sets}" if sets else "DO NOTHING"
                stmts.append((f"INSERT INTO {self.table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))}) "
                              f"ON CONFLICT({','.join(conflict)}) {action}", vals))
                continue
            # UNIQUE_KEYS에 없는 조합(processing_queue.video_id, videos.video_id+restaurant_id): 같은 요청(한 트랜잭션) 안에서
            # UPDATE 후 없을 때만 INSERT. 두 조합엔 고유 인덱스가 있지만(11/25) ON CONFLICT로 바꾸지 않는다:
            # 일부 칸만 넣는 upsert가 NOT NULL(channel_id 등)에 먼저 걸려 실패한다(11/25 시험)
            key_sql = " AND ".join(f"{_ident(c)} IS ?" for c in conflict)
            key_vals = [_param(row.get(c)) for c in conflict]
            if rest:
                stmts.append((f"UPDATE {self.table} SET {', '.join(f'{c}=?' for c in rest)} WHERE {key_sql}",
                              [_param(row[c]) for c in rest] + key_vals))
            stmts.append((f"INSERT INTO {self.table} ({','.join(cols)}) SELECT {','.join('?' * len(cols))} "
                          f"WHERE NOT EXISTS (SELECT 1 FROM {self.table} WHERE {key_sql})", vals + key_vals))
        batch(stmts)
        return Result([])

    def _x_update(self) -> Result:
        cols, vals = self._cols_vals(self._values)
        w, wp = self._where_sql()
        r = query(f"UPDATE {self.table} SET {', '.join(f'{c}=?' for c in cols)}{w}", vals + wp)
        return Result([], r["changes"])

    def _x_delete(self) -> Result:
        w, wp = self._where_sql()
        r = query(f"DELETE FROM {self.table}{w}", wp)
        return Result([], r["changes"])


class D1Client:
    def table(self, name: str) -> Query:
        return Query(name)

    @staticmethod
    def query(sql, params=None):
        return query(sql, params)

    @staticmethod
    def batch(stmts):
        return batch(stmts)


def get_d1() -> D1Client:
    _creds()
    return D1Client()

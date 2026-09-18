from __future__ import annotations
import json, sqlite3, asyncio
from datetime import datetime, timezone
from pathlib import Path

class RealtimeEventStore:
    def __init__(self, database_path):
        self.database_path=str(Path(database_path))

    @staticmethod
    def now(): return datetime.now(timezone.utc).isoformat()

    def publish(self, org, event_type, entity_type=None, entity_id=None, payload=None):
        with sqlite3.connect(self.database_path) as c:
            cur=c.execute("""INSERT INTO realtime_events
                (organization_id,event_type,entity_type,entity_id,payload_json,created_at)
                VALUES(?,?,?,?,?,?)""",(org,event_type,entity_type,entity_id,
                json.dumps(payload or {},ensure_ascii=False),self.now()))
            return cur.lastrowid

    def since(self, org, after=0, limit=100):
        with sqlite3.connect(self.database_path) as c:
            c.row_factory=sqlite3.Row
            rows=c.execute("""SELECT * FROM realtime_events
                WHERE organization_id=? AND id>? ORDER BY id LIMIT ?""",(org,int(after),int(limit))).fetchall()
        result=[]
        for r in rows:
            d=dict(r); d["payload"]=json.loads(d.pop("payload_json") or "{}"); result.append(d)
        return result

    async def stream(self, org, after=0):
        cursor=int(after)
        while True:
            rows=self.since(org,cursor,100)
            if rows:
                for row in rows:
                    cursor=row["id"]
                    yield "id: %s\nevent: %s\ndata: %s\n\n" % (
                        row["id"], row["event_type"], json.dumps(row,ensure_ascii=False,default=str))
            else:
                yield ": keepalive\n\n"
            await asyncio.sleep(2)

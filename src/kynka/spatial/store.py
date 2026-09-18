from __future__ import annotations
import json, sqlite3, uuid
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc).isoformat()

class SpatialStore:
    def __init__(self, database_path):
        self.database_path=str(database_path)

    def _connect(self):
        c=sqlite3.connect(self.database_path)
        c.row_factory=sqlite3.Row
        return c

    def create_multimodal_session(self, organization_id, user_id, device_id=None, locale="pt-PT"):
        sid=str(uuid.uuid4()); now=utcnow()
        with self._connect() as c:
            c.execute("""INSERT INTO multimodal_sessions
              (id,organization_id,user_id,device_id,locale,status,created_at,updated_at)
              VALUES(?,?,?,?,?,'active',?,?)""",(sid,organization_id,user_id,device_id,locale,now,now))
        return self.get_multimodal_session(organization_id,sid)

    def get_multimodal_session(self, organization_id, session_id):
        with self._connect() as c:
            r=c.execute("SELECT * FROM multimodal_sessions WHERE organization_id=? AND id=?",
                        (organization_id,session_id)).fetchone()
        return dict(r) if r else None

    def add_multimodal_event(self, organization_id, user_id, session_id, event_type, payload):
        now=utcnow()
        with self._connect() as c:
            cur=c.execute("""INSERT INTO multimodal_events
              (organization_id,user_id,session_id,event_type,payload_json,created_at)
              VALUES(?,?,?,?,?,?)""",
              (organization_id,user_id,session_id,event_type,json.dumps(payload,ensure_ascii=False),now))
            eid=cur.lastrowid
            c.execute("UPDATE multimodal_sessions SET updated_at=? WHERE organization_id=? AND id=?",
                      (now,organization_id,session_id))
        return eid

    def events(self, organization_id, session_id):
        with self._connect() as c:
            rows=c.execute("""SELECT id,event_type,payload_json,created_at FROM multimodal_events
              WHERE organization_id=? AND session_id=? ORDER BY id""",(organization_id,session_id)).fetchall()
        return [{"id":r["id"],"event_type":r["event_type"],
                 "payload":json.loads(r["payload_json"]),"created_at":r["created_at"]} for r in rows]

    def set_avatar_state(self, organization_id, user_id, avatar_id, state, expression, speaking_text=None, visemes=None):
        now=utcnow()
        payload=json.dumps(visemes or [],ensure_ascii=False)
        with self._connect() as c:
            c.execute("""INSERT INTO avatar_states
              (organization_id,user_id,avatar_id,state,expression,speaking_text,visemes_json,updated_at)
              VALUES(?,?,?,?,?,?,?,?)
              ON CONFLICT(organization_id,user_id,avatar_id) DO UPDATE SET
              state=excluded.state,expression=excluded.expression,speaking_text=excluded.speaking_text,
              visemes_json=excluded.visemes_json,updated_at=excluded.updated_at""",
              (organization_id,user_id,avatar_id,state,expression,speaking_text,payload,now))
        return self.avatar_state(organization_id,user_id,avatar_id)

    def avatar_state(self, organization_id, user_id, avatar_id):
        with self._connect() as c:
            r=c.execute("""SELECT * FROM avatar_states
              WHERE organization_id=? AND user_id=? AND avatar_id=?""",
              (organization_id,user_id,avatar_id)).fetchone()
        if not r:return None
        d=dict(r);d["visemes"]=json.loads(d.pop("visemes_json"));return d

    def create_spatial_session(self, organization_id, user_id, device_id=None, client="generic-ar"):
        sid=str(uuid.uuid4());now=utcnow()
        with self._connect() as c:
            c.execute("""INSERT INTO spatial_sessions
              (id,organization_id,user_id,device_id,client,status,created_at,updated_at)
              VALUES(?,?,?,?,?,'active',?,?)""",(sid,organization_id,user_id,device_id,client,now,now))
        return self.get_spatial_session(organization_id,sid)

    def get_spatial_session(self, organization_id, session_id):
        with self._connect() as c:
            r=c.execute("SELECT * FROM spatial_sessions WHERE organization_id=? AND id=?",
                        (organization_id,session_id)).fetchone()
        return dict(r) if r else None

    def upsert_anchor(self, organization_id, session_id, anchor_id, label, transform):
        now=utcnow()
        with self._connect() as c:
            c.execute("""INSERT INTO spatial_anchors
              (organization_id,session_id,anchor_id,label,transform_json,updated_at)
              VALUES(?,?,?,?,?,?)
              ON CONFLICT(organization_id,session_id,anchor_id) DO UPDATE SET
              label=excluded.label,transform_json=excluded.transform_json,updated_at=excluded.updated_at""",
              (organization_id,session_id,anchor_id,label,json.dumps(transform),now))
        return {"anchor_id":anchor_id,"label":label,"transform":transform,"updated_at":now}

    def upsert_object(self, organization_id, session_id, object_id, kind, label, anchor_id, transform, resource):
        now=utcnow()
        with self._connect() as c:
            c.execute("""INSERT INTO spatial_objects
              (organization_id,session_id,object_id,kind,label,anchor_id,transform_json,resource_json,updated_at)
              VALUES(?,?,?,?,?,?,?,?,?)
              ON CONFLICT(organization_id,session_id,object_id) DO UPDATE SET
              kind=excluded.kind,label=excluded.label,anchor_id=excluded.anchor_id,
              transform_json=excluded.transform_json,resource_json=excluded.resource_json,updated_at=excluded.updated_at""",
              (organization_id,session_id,object_id,kind,label,anchor_id,
               json.dumps(transform),json.dumps(resource),now))
        return {"object_id":object_id,"kind":kind,"label":label,"anchor_id":anchor_id,
                "transform":transform,"resource":resource,"updated_at":now}

    def scene(self, organization_id, session_id):
        with self._connect() as c:
            anchors=c.execute("""SELECT * FROM spatial_anchors WHERE organization_id=? AND session_id=?
              ORDER BY anchor_id""",(organization_id,session_id)).fetchall()
            objects=c.execute("""SELECT * FROM spatial_objects WHERE organization_id=? AND session_id=?
              ORDER BY object_id""",(organization_id,session_id)).fetchall()
        return {
          "protocol":"kynka-spatial/1.0",
          "coordinate_system":"right-handed-y-up",
          "units":"meters",
          "anchors":[{"anchor_id":r["anchor_id"],"label":r["label"],
                      "transform":json.loads(r["transform_json"]),"updated_at":r["updated_at"]} for r in anchors],
          "objects":[{"object_id":r["object_id"],"kind":r["kind"],"label":r["label"],
                      "anchor_id":r["anchor_id"],"transform":json.loads(r["transform_json"]),
                      "resource":json.loads(r["resource_json"]),"updated_at":r["updated_at"]} for r in objects]
        }

    def interaction(self, organization_id, user_id, session_id, interaction_type, object_id, payload):
        now=utcnow()
        with self._connect() as c:
            cur=c.execute("""INSERT INTO spatial_interactions
              (organization_id,user_id,session_id,interaction_type,object_id,payload_json,created_at)
              VALUES(?,?,?,?,?,?,?)""",
              (organization_id,user_id,session_id,interaction_type,object_id,
               json.dumps(payload,ensure_ascii=False),now))
        return {"id":cur.lastrowid,"interaction_type":interaction_type,
                "object_id":object_id,"payload":payload,"created_at":now}

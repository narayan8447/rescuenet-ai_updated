import sys
import types
import json
from typing import Any

# Create a genuine module object
ormsgpack_mock = types.ModuleType("ormsgpack")

class MsgpackEncodeError(Exception):
    pass
    
class Ext:
    def __init__(self, type_id: int, data: bytes):
        self.type = type_id
        self.data = data

OPT_NON_STR_KEYS = 1
OPT_PASSTHROUGH_DATACLASS = 2
OPT_PASSTHROUGH_DATETIME = 4
OPT_PASSTHROUGH_ENUM = 8
OPT_PASSTHROUGH_UUID = 16

def packb(data, default=None, option=None):
    def default_wrapper(obj):
        if isinstance(obj, Ext):
            return {"__ext__": True, "type": obj.type, "data": obj.data.hex()}
        if default:
            try:
                res = default(obj)
                if isinstance(res, Ext):
                    return {"__ext__": True, "type": res.type, "data": res.data.hex()}
                return res
            except Exception:
                pass
        raise TypeError(f"Object of type {obj.__class__.__name__} is not serializable")
        
    return json.dumps(data, default=default_wrapper).encode("utf-8")
    
def unpackb(data_bytes, ext_hook=None, option=None):
    decoded = json.loads(data_bytes.decode("utf-8"))
    
    def revive(obj):
        if isinstance(obj, dict):
            if obj.get("__ext__") is True:
                t = obj["type"]
                d = obj["data"]
                raw_data = bytes.fromhex(d)
                if ext_hook:
                    return ext_hook(t, raw_data)
                return Ext(t, raw_data)
            return {k: revive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [revive(x) for x in obj]
        return obj
        
    return revive(decoded)

# Assign attributes to the module
ormsgpack_mock.MsgpackEncodeError = MsgpackEncodeError
ormsgpack_mock.Ext = Ext
ormsgpack_mock.OPT_NON_STR_KEYS = OPT_NON_STR_KEYS
ormsgpack_mock.OPT_PASSTHROUGH_DATACLASS = OPT_PASSTHROUGH_DATACLASS
ormsgpack_mock.OPT_PASSTHROUGH_DATETIME = OPT_PASSTHROUGH_DATETIME
ormsgpack_mock.OPT_PASSTHROUGH_ENUM = OPT_PASSTHROUGH_ENUM
ormsgpack_mock.OPT_PASSTHROUGH_UUID = OPT_PASSTHROUGH_UUID
ormsgpack_mock.packb = packb
ormsgpack_mock.unpackb = unpackb

# Inject the module object into sys.modules
sys.modules["ormsgpack"] = ormsgpack_mock

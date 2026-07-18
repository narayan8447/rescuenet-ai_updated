import sys
import json
from typing import Any

class MockOrmsgpack:
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
    
    @staticmethod
    def packb(data, default=None, option=None):
        def default_wrapper(obj):
            if isinstance(obj, MockOrmsgpack.Ext):
                return {"__ext__": True, "type": obj.type, "data": obj.data.hex()}
            if default:
                try:
                    res = default(obj)
                    if isinstance(res, MockOrmsgpack.Ext):
                        return {"__ext__": True, "type": res.type, "data": res.data.hex()}
                    return res
                except Exception:
                    pass
            raise TypeError(f"Object of type {obj.__class__.__name__} is not serializable")
            
        return json.dumps(data, default=default_wrapper).encode("utf-8")
        
    @staticmethod
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
                    return MockOrmsgpack.Ext(t, raw_data)
                return {k: revive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [revive(x) for x in obj]
            return obj
            
        return revive(decoded)

# Inject mock into sys.modules
sys.modules["ormsgpack"] = MockOrmsgpack

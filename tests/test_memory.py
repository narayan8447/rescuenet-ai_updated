import pytest
import os
from backend.core.memory import RedisMemoryManager, RedisSaver
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata, SerializerProtocol
import json

class MockSerializer(SerializerProtocol):
    def dumps(self, obj) -> bytes:
        return json.dumps(obj).encode("utf-8")
        
    def loads(self, data: bytes):
        return json.loads(data.decode("utf-8"))

def test_redis_memory_manager():
    # Force use of fakeredis
    manager = RedisMemoryManager(use_fake=True)
    
    # Test setting and getting
    manager.set("test_key", {"status": "ok"})
    val = manager.get("test_key")
    assert val == {"status": "ok"}
    
    # Test deleting
    manager.delete("test_key")
    assert manager.get("test_key") is None
    
    # Test locks
    lock1 = manager.acquire_lock("resource_1", timeout=1)
    assert lock1 is True
    
    lock2 = manager.acquire_lock("resource_1", timeout=1)
    assert lock2 is False # Should fail since it's already locked
    
    manager.release_lock("resource_1")
    lock3 = manager.acquire_lock("resource_1", timeout=1)
    assert lock3 is True # Should succeed now

def test_redis_saver():
    manager = RedisMemoryManager(use_fake=True)
    saver = RedisSaver(manager.client, serde=MockSerializer())
    
    config = {"configurable": {"thread_id": "test_thread_1"}}
    checkpoint = {"v": 1, "id": "1", "ts": "2024-01-01T00:00:00Z", "channel_values": {"state": "data"}}
    metadata = {"source": "input"}
    
    # Put checkpoint
    new_config = saver.put(config, checkpoint, metadata)
    assert new_config["configurable"]["thread_ts"] == "1"
    
    # Get latest
    tup = saver.get_tuple(config)
    assert tup is not None
    assert tup.checkpoint["id"] == "1"
    assert tup.metadata["source"] == "input"
    
    # Put a newer checkpoint
    checkpoint2 = {"v": 1, "id": "2", "ts": "2024-01-01T00:00:01Z", "channel_values": {"state": "data2"}}
    metadata2 = {"source": "update"}
    saver.put(config, checkpoint2, metadata2)
    
    # Get latest again
    tup2 = saver.get_tuple(config)
    assert tup2.checkpoint["id"] == "2"
    
    # Get specific ts
    specific_config = {"configurable": {"thread_id": "test_thread_1", "thread_ts": "1"}}
    tup_old = saver.get_tuple(specific_config)
    assert tup_old.checkpoint["id"] == "1"
    
    # List checkpoints
    checkpoints = list(saver.list(config))
    assert len(checkpoints) == 2

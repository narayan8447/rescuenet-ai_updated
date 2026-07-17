import os
import json
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Iterator, AsyncIterator, Sequence
import asyncio
from functools import partial
import redis
import fakeredis
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple, SerializerProtocol
from langchain_core.runnables import RunnableConfig

class MemoryInterface(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> None:
        pass
        
    @abstractmethod
    def delete(self, key: str) -> None:
        pass

    @abstractmethod
    def acquire_lock(self, lock_name: str, timeout: int = 10) -> bool:
        pass

    @abstractmethod
    def release_lock(self, lock_name: str) -> None:
        pass

class RedisMemoryManager(MemoryInterface):
    def __init__(self, use_fake: bool = False):
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        if use_fake or os.environ.get("USE_FAKE_REDIS", "false").lower() == "true":
            self.client = fakeredis.FakeRedis()
        else:
            self.client = redis.Redis.from_url(redis_url)
            
    def get(self, key: str) -> Optional[Any]:
        val = self.client.get(key)
        if val is None:
            return None
        return json.loads(val)
        
    def set(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> None:
        val = json.dumps(value)
        self.client.set(key, val, ex=expire_seconds)
        
    def delete(self, key: str) -> None:
        self.client.delete(key)
        
    def acquire_lock(self, lock_name: str, timeout: int = 10) -> bool:
        return self.client.set(f"lock:{lock_name}", "locked", nx=True, ex=timeout) is not None
        
    def release_lock(self, lock_name: str) -> None:
        self.client.delete(f"lock:{lock_name}")

# Global Memory Manager
memory_manager = RedisMemoryManager()

class RedisSaver(BaseCheckpointSaver):
    """
    A LangGraph CheckpointSaver that persists checkpoints and writes to Redis.
    """
    def __init__(self, client: redis.Redis, *, serde: Optional[SerializerProtocol] = None) -> None:
        super().__init__(serde=serde)
        self.client = client

    def _get_pending_writes(self, thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> list[tuple[str, str, Any]]:
        writes_key = f"writes:{thread_id}:{checkpoint_ns}:{checkpoint_id}"
        writes_data = self.client.hgetall(writes_key)
        pending_writes = []
        if writes_data:
            for field, val_b in writes_data.items():
                val_str = val_b.decode('utf-8') if isinstance(val_b, bytes) else val_b
                task_id_saved, channel_saved, val_hex, task_path_saved = json.loads(val_str)
                deserialized_val = self.serde.loads(bytes.fromhex(val_hex))
                pending_writes.append((task_id_saved, channel_saved, deserialized_val))
        return pending_writes

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        ts = config["configurable"].get("thread_ts") or config["configurable"].get("checkpoint_id")
        
        key = f"checkpoint:{thread_id}"
        
        if ts:
            saved = self.client.hget(key, ts)
            if saved:
                checkpoint_b, metadata_b = json.loads(saved)
                pending_writes = self._get_pending_writes(thread_id, checkpoint_ns, ts)
                return CheckpointTuple(
                    config=config,
                    checkpoint=self.serde.loads(bytes.fromhex(checkpoint_b)),
                    metadata=self.serde.loads(bytes.fromhex(metadata_b)),
                    pending_writes=pending_writes,
                )
        else:
            # Get all fields and values
            all_saved = self.client.hgetall(key)
            if all_saved:
                keys_str = [k.decode('utf-8') if isinstance(k, bytes) else k for k in all_saved.keys()]
                latest_ts = max(keys_str)
                latest_saved = all_saved[latest_ts.encode('utf-8') if isinstance(list(all_saved.keys())[0], bytes) else latest_ts]
                
                checkpoint_b, metadata_b = json.loads(latest_saved)
                pending_writes = self._get_pending_writes(thread_id, checkpoint_ns, latest_ts)
                return CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": latest_ts,
                            "thread_ts": latest_ts,
                        }
                    },
                    checkpoint=self.serde.loads(bytes.fromhex(checkpoint_b)),
                    metadata=self.serde.loads(bytes.fromhex(metadata_b)),
                    pending_writes=pending_writes,
                )
        return None

    def list(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        
        thread_ids = [config["configurable"]["thread_id"]] if config else []
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "") if config else ""
        if not thread_ids:
            for k in self.client.scan_iter("checkpoint:*"):
                thread_id = k.decode('utf-8').split(":", 1)[1] if isinstance(k, bytes) else k.split(":", 1)[1]
                thread_ids.append(thread_id)

        for thread_id in thread_ids:
            key = f"checkpoint:{thread_id}"
            all_saved = self.client.hgetall(key)
            for ts_b, val_b in all_saved.items():
                ts = ts_b.decode('utf-8') if isinstance(ts_b, bytes) else ts_b
                
                before_ts = before["configurable"].get("thread_ts") or before["configurable"].get("checkpoint_id") if before else None
                if before_ts and ts >= before_ts:
                    continue
                    
                checkpoint_b, metadata_b = json.loads(val_b)
                metadata = self.serde.loads(bytes.fromhex(metadata_b))
                
                if filter and not all(query_value == metadata.get(query_key) for query_key, query_value in filter.items()):
                    continue
                    
                if limit is not None and limit <= 0:
                    break
                elif limit is not None:
                    limit -= 1
                    
                pending_writes = self._get_pending_writes(thread_id, checkpoint_ns, ts)
                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": ts,
                            "thread_ts": ts,
                        }
                    },
                    checkpoint=self.serde.loads(bytes.fromhex(checkpoint_b)),
                    metadata=metadata,
                    pending_writes=pending_writes,
                )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        *args: Any,
        **kwargs: Any,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        ts = checkpoint["id"]
        key = f"checkpoint:{thread_id}"
        
        checkpoint_hex = self.serde.dumps(checkpoint).hex()
        metadata_hex = self.serde.dumps(metadata).hex()
        
        val = json.dumps([checkpoint_hex, metadata_hex])
        self.client.hset(key, ts, val)
        
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": ts,
                "thread_ts": ts,
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]
        
        key = f"writes:{thread_id}:{checkpoint_ns}:{checkpoint_id}"
        
        for idx, (channel, val) in enumerate(writes):
            val_hex = self.serde.dumps(val).hex()
            field = f"{task_id}:{idx}"
            val_data = json.dumps([task_id, channel, val_hex, task_path])
            self.client.hset(key, field, val_data)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self.put_writes(config, writes, task_id, task_path)

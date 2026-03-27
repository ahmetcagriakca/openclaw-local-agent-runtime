"""Sprint 10 SSE Test Suite - FileWatcher, SSEManager, SSE endpoint.

Rules applied:
- All async queue.get() use asyncio.wait_for(timeout=5.0)
- SSE endpoint tests read only first events then break
- Heartbeat tests use heartbeat_interval_s=0.2 (not 30s)
- FileWatcher tests use mock mtime + manual _check_all() trigger
- Each async test wrapped in run_with_timeout (10s hard limit)
"""
import asyncio
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_TIMEOUT = 10.0


def run_with_timeout(coro, timeout=TEST_TIMEOUT):
    """Run an async coroutine with a hard timeout."""
    async def _wrapped():
        return await asyncio.wait_for(coro, timeout=timeout)
    return asyncio.run(_wrapped())


class TestFileWatcher(unittest.TestCase):

    def _make_watcher(self, tmppath, **overrides):
        from api.file_watcher import FileWatcher
        missions_dir = overrides.get("missions_dir", tmppath / "missions")
        approvals_dir = overrides.get("approvals_dir", tmppath / "approvals")
        missions_dir.mkdir(exist_ok=True)
        approvals_dir.mkdir(exist_ok=True)
        queue = asyncio.Queue(maxsize=100)
        watcher = FileWatcher(
            missions_dir=missions_dir,
            telemetry_path=overrides.get("telemetry_path", tmppath / "t.jsonl"),
            capabilities_path=overrides.get("capabilities_path", tmppath / "c.json"),
            services_path=overrides.get("services_path", tmppath / "s.json"),
            approvals_dir=approvals_dir,
            event_queue=queue,
        )
        return watcher, queue

    def _force_flush(self, watcher):
        for k in list(watcher._pending_events.keys()):
            event, _ = watcher._pending_events[k]
            watcher._pending_events[k] = (event, 0)
        watcher._flush_debounced()

    def _drain(self, queue):
        events = []
        while not queue.empty():
            events.append(queue.get_nowait())
        return events

    def test_01_mtime_change_produces_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            cap = p / "c.json"
            cap.write_text("{}")
            w, q = self._make_watcher(p, capabilities_path=cap)
            w._warm_cache()
            time.sleep(0.05)
            cap.write_text('{"v":1}')
            w._check_all()
            self._force_flush(w)
            evts = self._drain(q)
            self.assertEqual(len(evts), 1)
            self.assertEqual(evts[0].event_type, "capability_changed")

    def test_02_missing_file_no_crash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            w, q = self._make_watcher(
                p,
                telemetry_path=p / "nope.jsonl",
                capabilities_path=p / "nope.json",
                services_path=p / "nope_svc.json",
            )
            w._warm_cache()
            w._check_all()
            self._force_flush(w)
            self.assertTrue(q.empty())

    def test_03_new_mission_dir_produces_list_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            md = p / "missions"
            w, q = self._make_watcher(p, missions_dir=md)
            w._warm_cache()
            (md / "m-001").mkdir()
            w._check_all()
            self._force_flush(w)
            evts = self._drain(q)
            self.assertEqual(len(evts), 1)
            self.assertEqual(evts[0].event_type, "mission_list_changed")

    def test_04_debounce_merges_rapid_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            cap = p / "c.json"
            cap.write_text("{}")
            w, q = self._make_watcher(p, capabilities_path=cap)
            w._warm_cache()
            for i in range(3):
                time.sleep(0.05)
                cap.write_text(f'{{"v":{i}}}')
                w._check_all()
            self._force_flush(w)
            evts = self._drain(q)
            self.assertEqual(len(evts), 1)

    def test_05_mission_state_file_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            md = p / "missions"
            md.mkdir()
            mdir = md / "m-test"
            mdir.mkdir()
            sf = mdir / "m-test-state.json"
            sf.write_text('{"state":"pending"}')
            w, q = self._make_watcher(p, missions_dir=md)
            w._warm_cache()
            time.sleep(0.05)
            sf.write_text('{"state":"executing"}')
            w._check_all()
            self._force_flush(w)
            evts = self._drain(q)
            self.assertEqual(len(evts), 1)
            self.assertEqual(evts[0].event_type, "mission_updated")
            self.assertEqual(evts[0].data["missionId"], "m-test")


class TestSSEManager(unittest.TestCase):

    def test_06_subscribe_unsubscribe(self):
        from api.sse_manager import SSEManager
        async def _t():
            m = SSEManager()
            q = await m.subscribe()
            self.assertIsNotNone(q)
            self.assertEqual(m.client_count, 1)
            await m.unsubscribe(q)
            self.assertEqual(m.client_count, 0)
        run_with_timeout(_t())

    def test_07_broadcast_reaches_all(self):
        from api.sse_manager import SSEManager
        async def _t():
            m = SSEManager()
            q1 = await m.subscribe()
            q2 = await m.subscribe()
            await m.broadcast("test_ev", {"k": "v"})
            e1 = await asyncio.wait_for(q1.get(), timeout=5.0)
            e2 = await asyncio.wait_for(q2.get(), timeout=5.0)
            self.assertEqual(e1.event, "test_ev")
            self.assertEqual(e2.event, "test_ev")
            await m.unsubscribe(q1)
            await m.unsubscribe(q2)
        run_with_timeout(_t())

    def test_08_max_clients_rejection(self):
        from api.sse_manager import MAX_CLIENTS, SSEManager
        async def _t():
            m = SSEManager()
            qs = []
            for _ in range(MAX_CLIENTS):
                q = await m.subscribe()
                self.assertIsNotNone(q)
                qs.append(q)
            self.assertIsNone(await m.subscribe())
            for q in qs:
                await m.unsubscribe(q)
        run_with_timeout(_t())

    def test_09_missed_events_replay(self):
        from api.sse_manager import SSEManager
        async def _t():
            m = SSEManager()
            await m.broadcast("a", {"n": 1})
            await m.broadcast("b", {"n": 2})
            await m.broadcast("c", {"n": 3})
            missed = m.get_missed_events(1)
            self.assertEqual(len(missed), 2)
            self.assertEqual(missed[0].event, "b")
            self.assertEqual(missed[1].event, "c")
        run_with_timeout(_t())

    def test_10_sse_event_format(self):
        from api.sse_manager import SSEEvent
        ev = SSEEvent(id=42, event="test", data='{"k":"v"}')
        f = ev.format()
        self.assertIn("id: 42", f)
        self.assertIn("event: test", f)
        self.assertIn('data: {"k":"v"}', f)
        self.assertTrue(f.endswith("\n\n"))

    def test_11_shutdown_signals_clients(self):
        from api.sse_manager import SSEManager
        async def _t():
            m = SSEManager()
            q = await m.subscribe()
            await m.shutdown()
            item = await asyncio.wait_for(q.get(), timeout=5.0)
            self.assertIsNone(item)
            self.assertEqual(m.client_count, 0)
        run_with_timeout(_t())

    def test_12_heartbeat_fast(self):
        from api.sse_manager import SSEManager
        async def _t():
            m = SSEManager(heartbeat_interval_s=0.2)
            q = await m.subscribe()
            await m.start_heartbeat()
            ev = await asyncio.wait_for(q.get(), timeout=5.0)
            self.assertEqual(ev.event, "heartbeat")
            await m.shutdown()
        run_with_timeout(_t())


class TestSSEEndpoint(unittest.TestCase):

    @staticmethod
    def _make_stream_app():
        """Minimal app WITHOUT middleware — safe for SSE streaming tests."""
        from fastapi import FastAPI

        from api.sse_api import router as sse_router
        from api.sse_manager import SSEManager

        app = FastAPI()
        manager = SSEManager(heartbeat_interval_s=0.2)
        app.state.sse_manager = manager
        app.include_router(sse_router, prefix="/api/v1")
        return app, manager

    @staticmethod
    def _make_host_app():
        """App WITH host-validation middleware — for rejection tests."""
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        from api.sse_api import router as sse_router
        from api.sse_manager import SSEManager

        app = FastAPI()
        manager = SSEManager(heartbeat_interval_s=0.2)
        app.state.sse_manager = manager

        @app.middleware("http")
        async def validate_host(request, call_next):
            host = request.headers.get("host", "")
            allowed = {"localhost", "127.0.0.1", "testserver",
                       "localhost:8003", "127.0.0.1:8003"}
            if host not in allowed:
                return JSONResponse(status_code=403,
                    content={"error": "forbidden", "detail": "Invalid Host header"})
            return await call_next(request)

        app.include_router(sse_router, prefix="/api/v1")
        return app, manager

    def test_13_stream_connected_event(self):
        """Directly invoke sse_stream() - avoids ASGI transport SSE deadlock."""
        from unittest.mock import AsyncMock

        from api.sse_api import sse_stream
        from api.sse_manager import SSEManager

        async def _t():
            manager = SSEManager(heartbeat_interval_s=300)

            # Mock request
            request = AsyncMock()
            request.app.state.sse_manager = manager
            request.headers = {}
            # is_disconnected: False first, then True after we read connected event
            disconnect_after = 0
            call_count = 0
            async def fake_disconnected():
                nonlocal call_count
                call_count += 1
                return call_count > disconnect_after
            request.is_disconnected = fake_disconnected

            response = await sse_stream(request)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.media_type, "text/event-stream")

            # Read first chunk: connected event
            first_chunk = await asyncio.wait_for(
                response.body_iterator.__anext__(), timeout=5.0
            )
            self.assertIn("event: connected", first_chunk)
            self.assertIn("serverTime", first_chunk)
            self.assertIn("version", first_chunk)

            # Now signal disconnect so generator exits cleanly
            disconnect_after = 0  # next is_disconnected() returns True

            # Drain generator - it should exit within timeout cycles
            try:
                async for _ in response.body_iterator:
                    break  # just in case there's buffered data
            except (StopAsyncIteration, asyncio.CancelledError):
                pass

            await manager.shutdown()

        run_with_timeout(_t())

    def test_14_host_validation_rejects(self):
        from fastapi.testclient import TestClient
        test_app, _manager = self._make_host_app()
        with TestClient(test_app) as client:
            r = client.get("/api/v1/events/stream", headers={"Host": "evil.com"})
            self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()

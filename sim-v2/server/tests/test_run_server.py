from __future__ import annotations

import socket

import pytest

from run_server import find_available_port


def test_find_available_port_falls_back_when_port_in_use(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, int]] = []

    class _DummyServer:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_create_server(addr, reuse_port=False):
        host, port = addr
        calls.append((host, port))
        if len(calls) == 1:
            raise OSError("Address already in use")
        return _DummyServer()

    monkeypatch.setattr(socket, "create_server", fake_create_server)

    chosen_port, did_fallback = find_available_port("127.0.0.1", 8000, max_tries=10)

    assert did_fallback is True
    assert chosen_port == 8001
    assert calls == [("127.0.0.1", 8000), ("127.0.0.1", 8001)]


def test_find_available_port_rejects_invalid_max_tries():
    try:
        find_available_port("127.0.0.1", 8000, max_tries=0)
        assert False, "expected ValueError"
    except ValueError:
        pass

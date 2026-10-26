"""Exercise real SDK/aiohttp proxy routing against a local test proxy."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from bilibili_api import get_client, get_selected_client, request_settings, select_client

from bili_cli import client


@asynccontextmanager
async def local_proxy(monkeypatch, body=b'{"body":[{"content":"proxy subtitle"}]}'):
    requests = []

    async def handle(reader, writer):
        requests.append((await reader.readline()).decode().strip())
        await reader.readuntil(b"\r\n\r\n")
        writer.write(
            b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode()
            + body
        )
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    url = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}"
    for key in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        monkeypatch.setenv(key, url)
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setenv("no_proxy", "")
    async with server:
        yield requests


@pytest.mark.asyncio
async def test_sdk_uses_environment_proxy_for_public_requests(monkeypatch):
    previous_backend = get_selected_client()[0]
    previous_settings = request_settings.get_all().copy()
    select_client("aiohttp")
    request_settings.set("proxy", "")
    request_settings.set("trust_env", True)
    sdk = None

    async def request():
        nonlocal sdk
        sdk = get_client()
        return await sdk.request(method="GET", url="http://bili-proxy-test.invalid/video")

    try:
        async with local_proxy(monkeypatch) as requests:
            response = await client._call_api("public test", request())
            assert response.code == 200
            assert requests == ["GET http://bili-proxy-test.invalid/video HTTP/1.1"]
    finally:
        if sdk:
            await sdk.close()
        for key, value in previous_settings.items():
            request_settings.set(key, value)
        select_client(previous_backend)


@pytest.mark.asyncio
async def test_subtitle_download_uses_environment_proxy(monkeypatch):
    with patch("bili_cli.client.video.Video") as video:
        video.return_value.get_pages = AsyncMock(return_value=[{"cid": 1}])
        video.return_value.get_player_info = AsyncMock(return_value={
            "subtitle": {"subtitles": [{"lan": "zh-CN", "subtitle_url": "http://bili-proxy-test.invalid/sub.json"}]},
        })
        async with local_proxy(monkeypatch) as requests:
            text, _items = await client.get_video_subtitle("BV1d8pU6xEZX")
            assert text == "proxy subtitle"
            assert requests == ["GET http://bili-proxy-test.invalid/sub.json HTTP/1.1"]


@pytest.mark.asyncio
@pytest.mark.parametrize("proxy,trust_env", [("http://configured.invalid:8888", True), ("", False)])
async def test_preserves_explicit_sdk_transport_settings(proxy, trust_env):
    settings = request_settings.get_all().copy()
    try:
        request_settings.set("proxy", proxy)
        request_settings.set("trust_env", trust_env)
        result = await client._call_api("no request", AsyncMock(return_value="ok")())
        assert result == "ok"
        assert request_settings.get_proxy() == proxy
        assert request_settings.get_trust_env() == trust_env
    finally:
        for key, value in settings.items():
            request_settings.set(key, value)

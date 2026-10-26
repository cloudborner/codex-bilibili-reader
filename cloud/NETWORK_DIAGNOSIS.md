# Cloud network diagnosis

## Code findings and fix

The locked bilibili-api-python 17.4.1 aiohttp backend passes `proxy=""`
explicitly. aiohttp treats that differently from `proxy=None`: an empty proxy
suppresses lookup of HTTP_PROXY/HTTPS_PROXY even when trust_env=True.

A local fake proxy reproduced both paths without reaching any external site:

```text
inherit_environment proxy_reached=True
sdk_empty_proxy proxy_reached=False
```

The application now normalizes only the aiohttp SDK's empty default proxy to
None when trust_env is already enabled. Explicit proxies, other backends,
TLS verification and explicit trust_env=False settings are preserved. aiohttp
retains normal NO_PROXY handling. Direct subtitle/comment/audio sessions now
also use trust_env=True.

Four regression cases include real requests to a local fake proxy through the
SDK and the subtitle downloader, plus preservation of explicit proxy and
trust settings. Full local validation: 207 passed, 5 authenticated smoke tests
deselected; Ruff and mypy passed.

## Independent cloud result

The continuing cloud task compared api.github.com, pypi.org,
www.bilibili.com and the Bilibili public view API through the normal platform
proxy, using curl and aiohttp with trust_env=True. Three rounds gave the same
result:

- proxy:8080 resolves, but TCP connection fails with PermissionError /
  Operation not permitted.
- curl exits 7, with HTTP and CONNECT status 000.
- aiohttp reports a proxy connection error.
- No target website response, no CONNECT 403 and no Bilibili business response.

This is a separate runtime egress problem. Correcting proxy inheritance cannot
make an unreachable platform proxy available. This evidence does not establish
a country restriction or a Bilibili anti-bot response.

The cloud report is reports/网络分层重试.md in the continuing task:
https://chatgpt.com/local/01a17627-917b-76a2-bd5b-018f2483c03c

No proxy removal, direct-IP route, TLS bypass, Bilibili login or interaction was
used in the cloud diagnosis.

from starlette.requests import Request

from app.services.rate_limit import client_ip


def test_client_ip_ignores_untrusted_forwarded_header():
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"x-forwarded-for", b"203.0.113.77")],
            "client": ("10.0.0.8", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
            "root_path": "",
            "http_version": "1.1",
        }
    )

    assert client_ip(request) == "10.0.0.8"

from unittest.mock import MagicMock, Mock

from apiclient.request_strategies import BaseRequestStrategy

from nordigen import Client


class AsyncMagicMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMagicMock, self).__call__(*args, **kwargs)


def test_client(token="secret-token", request_strategy=Mock(spec=BaseRequestStrategy)):
    return Client(token=token, request_strategy=request_strategy)

"""Client code"""
import asyncio
import logging
import sys

from . import _read_packet, _write_packet, CommandCodes, AnswerCodes, CommandPacket, ResponsePacket, ResponseException

_LOGGER = logging.getLogger(__name__)
_REQUEST_TIMEOUT = 3


class Client:
    def __init__(self, host, port, loop) -> None:
        self._reader = None
        self._writer = None
        self._loop = loop
        self._task = None
        self._listen = set()
        self._host = host
        self._port = port

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def _process(self):
        while True:
            packet = await _read_packet(self._reader)
            if packet is None:
                _LOGGER.debug("Server disconnected")
                return

            _LOGGER.debug("Packet received: %s", packet)
            for l in self._listen:
                l(packet)

    async def start(self):
        _LOGGER.debug("Starting client")
        if self._task:
            raise Exception("Already started")

        self._reader, self._writer = await asyncio.open_connection(
            self._host, self._port, loop=self._loop)

        self._task = asyncio.ensure_future(
            self._process(), loop=self._loop)

    async def stop(self):
        _LOGGER.debug("Stopping client")
        if self._task:
            self._task.cancel()
            asyncio.wait(self._task)
        self._writer.close()
        if (sys.version_info >= (3, 7)):
            await self._writer.wait_closed()

        self._writer = None
        self._reader = None

    async def _request(self, request: CommandPacket):
        _LOGGER.debug("Requesting %s", request)
        result = None
        event  = asyncio.Event()

        def listen(response: ResponsePacket):
            if (response.zn == request.zn and 
                response.cc == request.cc):
                nonlocal result
                result = response
                event.set()

        self._listen.add(listen)
        await _write_packet(self._writer, request)
        await asyncio.wait_for(event.wait(), _REQUEST_TIMEOUT)
        return result

    async def request(self, zn, cc, data):
        response = await self._request(CommandPacket(zn, cc, data))

        if response.ac == AnswerCodes.STATUS_UPDATE:
            return response.data

        raise ResponseException(response)
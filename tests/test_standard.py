"""Standard tests for component"""
import asyncio
import arcam_av
import pytest
from unittest.mock import MagicMock, call

async def test_reader_valid(loop):
    reader = asyncio.StreamReader(loop=loop)
    reader.feed_data(b'\x21\x01\x08\x00\x02\x10\x10\x0D')
    reader.feed_eof()
    packet = await arcam_av._read_packet(reader)
    assert packet == arcam_av.ResponsePacket(1, 8 , 0, b'\x10\x10')


async def test_reader_invalid_data(loop):
    reader = asyncio.StreamReader(loop=loop)
    reader.feed_data(b'\x21\x01\x08\x00\x02\x10\x0D')
    reader.feed_eof()
    with pytest.raises(arcam_av.InvalidPacket):
        await arcam_av._read_packet(reader)


async def test_reader_short(loop):
    reader = asyncio.StreamReader(loop=loop)
    reader.feed_data(b'\x21\x10\x0D')
    reader.feed_eof()
    with pytest.raises(arcam_av.InvalidPacket):
        await arcam_av._read_packet(reader)


async def test_writer_valid(loop):
    writer = MagicMock()
    writer.write.return_value = None
    writer.drain.return_value = asyncio.Future()
    writer.drain.return_value.set_result(None)
    await arcam_av._write_packet(writer, arcam_av.CommandPacket(1, 8, b'\x10\x10'))
    writer.write.assert_has_calls([
        call(b'\x21'),
        call(b'\x01\x08\x02\x10\x10'),
        call(b'\x0D')
    ])
#!/usr/bin/env python3
"""Manual remote smoke test: run against a disposable DurableKV + BMC server.

Writes three keys. Requires BMC attached at native XDP and TC egress; server
counter deltas should show 5 SETs, 5 GET hits, 1 GET miss, and 6 XDP replies
when starting with empty maps. Does not test concurrent cache coherence.
"""
import socket
import struct
import sys

server = (sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 11211)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3)
request_id = 1000


def request(body, expected):
    global request_id
    request_id += 1
    header = struct.pack('!4H', request_id, 0, 1, 0)
    sock.sendto(header + body, server)
    reply, _ = sock.recvfrom(2048)
    assert reply == header + expected, (request_id, body, reply, expected)


def put(key, value):
    assert len(key) == 16 and len(value) == 32
    request(b'set ' + key + b' 0 0 32\r\n' + value + b'\r\n', b'STORED\r\n')


def get(key, value):
    expected = b'END\r\n' if value is None else (
        b'VALUE ' + key + b' 0 32\r\n' + value + b'\r\nEND\r\n')
    request(b'get ' + key + b'\r\n', expected)


key1, key2 = b'0000000000000001', b'0000000000000002'
for value in (b'A' * 32, b'B' * 32):
    put(key1, value)
    get(key1, value)
    get(key1, value)
put(key2, b'C' * 32)
get(key2, b'C' * 32)
get(key2, b'C' * 32)
embedded = b'set ' + key2 + b' ' + b'X' * 11
put(key1, embedded)
get(key1, embedded)
get(key1, embedded)
get(key2, b'C' * 32)
get(b'9999999999999999', None)
punctuation = b'punct!@#$%^&*()-'
put(punctuation, b'P' * 32)
get(punctuation, b'P' * 32)
get(punctuation, b'P' * 32)
sock.close()
print('PASS: 5 UDP SET acknowledgements, 11 GET hits, 1 miss; exact payloads and IDs')

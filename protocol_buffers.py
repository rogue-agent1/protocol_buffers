#!/usr/bin/env python3
"""protocol_buffers — Minimal protobuf-style binary serialization. Zero deps."""
import struct

VARINT, FIXED64, LENGTH_DELIMITED, FIXED32 = 0, 1, 2, 5

def encode_varint(value):
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)

def decode_varint(data, pos=0):
    result, shift = 0, 0
    while True:
        b = data[pos]
        result |= (b & 0x7F) << shift
        pos += 1
        if not (b & 0x80): break
        shift += 7
    return result, pos

def encode_field(field_num, wire_type, value):
    tag = encode_varint((field_num << 3) | wire_type)
    if wire_type == VARINT:
        return tag + encode_varint(value)
    elif wire_type == LENGTH_DELIMITED:
        if isinstance(value, str): value = value.encode()
        return tag + encode_varint(len(value)) + value
    elif wire_type == FIXED32:
        return tag + struct.pack('<I', value)
    elif wire_type == FIXED64:
        return tag + struct.pack('<Q', value)

def decode_message(data):
    fields = {}
    pos = 0
    while pos < len(data):
        tag, pos = decode_varint(data, pos)
        field_num = tag >> 3
        wire_type = tag & 0x07
        if wire_type == VARINT:
            value, pos = decode_varint(data, pos)
        elif wire_type == LENGTH_DELIMITED:
            length, pos = decode_varint(data, pos)
            value = data[pos:pos+length]
            pos += length
            try: value = value.decode()
            except: pass
        elif wire_type == FIXED32:
            value = struct.unpack('<I', data[pos:pos+4])[0]
            pos += 4
        elif wire_type == FIXED64:
            value = struct.unpack('<Q', data[pos:pos+8])[0]
            pos += 8
        else:
            raise ValueError(f"Unknown wire type: {wire_type}")
        fields[field_num] = value
    return fields

class Message:
    def __init__(self, schema):
        self.schema = schema  # {field_num: (name, wire_type)}
        self.fields = {}

    def set(self, name, value):
        for num, (n, _) in self.schema.items():
            if n == name: self.fields[num] = value; return
        raise KeyError(f"Unknown field: {name}")

    def encode(self):
        data = b''
        for num, value in sorted(self.fields.items()):
            _, wire_type = self.schema[num]
            data += encode_field(num, wire_type, value)
        return data

    def decode(self, data):
        raw = decode_message(data)
        result = {}
        for num, value in raw.items():
            if num in self.schema:
                name, _ = self.schema[num]
                result[name] = value
        return result

def main():
    schema = {1: ("id", VARINT), 2: ("name", LENGTH_DELIMITED), 3: ("email", LENGTH_DELIMITED), 4: ("age", VARINT)}
    msg = Message(schema)
    msg.set("id", 42)
    msg.set("name", "Rogue")
    msg.set("email", "rogue@example.com")
    msg.set("age", 1)
    encoded = msg.encode()
    print(f"Protobuf-style serialization:\n")
    print(f"  Original: id=42, name=Rogue, email=rogue@example.com, age=1")
    print(f"  Encoded:  {len(encoded)} bytes -> {encoded.hex()}")
    decoded = msg.decode(encoded)
    print(f"  Decoded:  {decoded}")
    print(f"  Varint(300) = {encode_varint(300).hex()} ({len(encode_varint(300))} bytes)")

if __name__ == "__main__":
    main()

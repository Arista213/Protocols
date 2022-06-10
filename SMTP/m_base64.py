BASE64_LINE = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
EQ_ORD = ord('=')


def encode(data: (bytes, str)):
    if isinstance(data, str):
        data = data.encode('utf8')
    result = bytearray()
    for i in range(0, len(data), 3):
        delta = min(3, len(data) - i)
        number = bin(int.from_bytes(data[i:i + 3], 'big'))[2:].zfill(8 * delta).ljust(6 * (delta + 1), '0')
        for j in range(0, len(number), 6):
            result.append(BASE64_LINE[int(number[j:j + 6], 2)])
        result.extend(b'=' * (3 - delta))

    return bytes(result)

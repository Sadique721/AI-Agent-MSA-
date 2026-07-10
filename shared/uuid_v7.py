import os
import time
import uuid
from typing import Sequence

def generate_uuid_v7() -> uuid.UUID:
    """
    Generates a timestamp-sortable UUID v7.
    Layout:
      - 48 bits: Unix timestamp in milliseconds
      - 4 bits: Version 7 (0111 binary)
      - 12 bits: Sequence counter or fraction
      - 2 bits: Variant 10 (10 binary)
      - 62 bits: Cryptographically strong pseudo-random bits
    """
    # Millisecond timestamp
    msec = int(time.time() * 1000)
    
    # 48-bit timestamp value
    ts_bytes = msec.to_bytes(6, byteorder='big')
    
    # Random bytes
    rand_bytes = os.urandom(10)
    
    # Construct bytes array
    uuid_bytes = bytearray(16)
    
    # Copy timestamp (first 6 bytes)
    uuid_bytes[0:6] = ts_bytes
    
    # Copy random part and inject version + variant
    # Version 7 at bits 48..51 (first 4 bits of byte 6)
    # Clear version bits and set to 7 (0x70)
    uuid_bytes[6] = (rand_bytes[0] & 0x0F) | 0x70
    uuid_bytes[7] = rand_bytes[1]
    
    # Variant at bits 64..65 (first 2 bits of byte 8)
    # Clear variant bits and set to 2 (0x80)
    uuid_bytes[8] = (rand_bytes[2] & 0x3F) | 0x80
    uuid_bytes[9:16] = rand_bytes[3:10]
    
    return uuid.UUID(bytes=bytes(uuid_bytes))

if __name__ == "__main__":
    u = generate_uuid_v7()
    print("Generated UUID v7:", u)

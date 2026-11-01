import pathlib

import zstandard as zstd


src = pathlib.Path("/Users/alissachang/大專/第一版.blend")
dst = pathlib.Path("/Users/alissachang/大專/第一版_decompressed.blend")

data = src.read_bytes()
dctx = zstd.ZstdDecompressor()
with dctx.stream_reader(src.open("rb")) as reader:
    chunks = []
    while True:
        chunk = reader.read(65536)
        if not chunk:
            break
        chunks.append(chunk)
out = b"".join(chunks)
dst.write_bytes(out)

print(dst)
print(len(data), "->", len(out))
print(out[:12])

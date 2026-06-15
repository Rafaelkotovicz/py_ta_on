"""Servidor HTTP minimalista sobre uasyncio.

Por que uasyncio (e nao socket bloqueante ou threads):
- Um unico event loop atende web + NFC + botoes sem _threads, que sao
  caras em RAM no ESP32.
- Conexoes sao processadas e fechadas (Connection: close), evitando
  sockets pendurados.
- Arquivos estaticos sao enviados em STREAMING (chunks de 512 B): a
  pagina nunca e carregada inteira na RAM.
- `gc.collect()` ao fim de cada requisicao recupera memoria.
"""

import uasyncio as asyncio
import gc

CHUNK = 512


async def _read_exact(reader, n):
    """Le exatamente n bytes (o corpo do POST) tolerando leituras parciais."""
    buf = b""
    while len(buf) < n:
        chunk = await reader.read(n - len(buf))
        if not chunk:
            break
        buf += chunk
    return buf


class WebServer:

    def __init__(self, router, host="0.0.0.0", port=80):
        self._router = router
        self._host = host
        self._port = port

    async def start(self):
        await asyncio.start_server(self._handle, self._host, self._port)

    async def _handle(self, reader, writer):
        path = "?"
        try:
            req_line = await reader.readline()
            if not req_line:
                return
            parts = req_line.split(b" ")
            if len(parts) < 2:
                return
            method = parts[0].decode()
            path = parts[1].decode()

            content_length = 0
            while True:
                line = await reader.readline()
                if not line or line == b"\r\n":
                    break
                if line.lower().startswith(b"content-length:"):
                    try:
                        content_length = int(line.split(b":", 1)[1].strip())
                    except ValueError:
                        content_length = 0

            body = b""
            if content_length > 0:
                body = await _read_exact(reader, content_length)

            print("HTTP", method, path)
            resp = await self._router.resolve(method, path, body)
            await self._send(writer, resp)
        except Exception as e:
            print("HTTP erro", path, e)
            try:
                await self._send(writer, {
                    "kind": "text",
                    "status": "500 Internal Server Error",
                    "ctype": "text/plain",
                    "body": "Erro interno",
                })
            except Exception:
                pass
        finally:
            try:
                await writer.drain()
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            gc.collect()

    async def _send(self, writer, resp):
        if resp.get("kind") == "file":
            await self._send_file(writer, resp["path"], resp["ctype"])
            return
        body = resp.get("body", "")
        if isinstance(body, str):
            body = body.encode()
        status = resp.get("status", "200 OK")
        ctype = resp.get("ctype", "text/plain")
        header = ("HTTP/1.1 %s\r\nContent-Type: %s\r\n"
                  "Content-Length: %d\r\nConnection: close\r\n"
                  "Cache-Control: no-cache\r\n\r\n"
                  % (status, ctype, len(body)))
        writer.write(header.encode())
        writer.write(body)
        await writer.drain()

    async def _send_file(self, writer, path, ctype):
        try:
            f = open(path, "rb")
        except OSError:
            await self._send(writer, {
                "kind": "text",
                "status": "404 Not Found",
                "ctype": "text/plain",
                "body": "Arquivo nao encontrado",
            })
            return
        try:
            data = f.read()
            size = len(data)
        finally:
            f.close()
        header = ("HTTP/1.1 200 OK\r\nContent-Type: %s\r\n"
                  "Content-Length: %d\r\nConnection: close\r\n\r\n"
                  % (ctype, size))
        writer.write(header.encode())
        writer.write(data)
        await writer.drain()

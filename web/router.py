"""Roteamento HTTP -> (arquivos estaticos | API JSON).

O Router nao contem regra de negocio: ele apenas traduz rotas em
chamadas aos services/repositorios e serializa a resposta. Paginas sao
servidas como arquivos (streaming); as APIs retornam JSON pequeno para
o polling do dashboard.
"""

import json

STATIC = "web/static/"


class Router:

    def __init__(self, user_repo, log_repo, request_repo, request_service):
        self._users = user_repo
        self._logs = log_repo
        self._requests_repo = request_repo
        self._request_service = request_service

    # ----------------- helpers -----------------
    def _json(self, obj, status="200 OK"):
        return {
            "kind": "text",
            "status": status,
            "ctype": "application/json",
            "body": json.dumps(obj),
        }

    def _file(self, name, ctype):
        return {"kind": "file", "path": STATIC + name, "ctype": ctype}

    def _not_found(self):
        return {
            "kind": "text",
            "status": "404 Not Found",
            "ctype": "text/plain",
            "body": "Nao encontrado",
        }

    def _parse_id(self, body):
        if not body:
            return None
        try:
            s = body.decode().strip()
        except Exception:
            return None
        if s.startswith("{"):
            try:
                return json.loads(s).get("id")
            except ValueError:
                return None
        for pair in s.split("&"):
            if pair.startswith("id="):
                return pair[3:]
        return None

    def _stats(self):
        ls = self._logs.stats()
        return {
            "usuarios": self._users.count(),
            "acessos": ls["total"],
            "liberados": ls["liberados"],
            "negados": ls["negados"],
            "pendentes": self._requests_repo.count_pending(),
        }

    # ----------------- resolucao -----------------
    async def resolve(self, method, path, body):
        q = path.find("?")
        if q >= 0:
            path = path[:q]

        # iOS/Android: sem isso o celular pode usar 4G e a API falha
        if path in ("/hotspot-detect.html", "/library/test/success.html",
                    "/generate_204", "/connecttest.txt", "/success.txt"):
            return {
                "kind": "text",
                "status": "200 OK",
                "ctype": "text/html",
                "body": "<html><body>OK</body></html>",
            }

        if method == "GET":
            if path == "/" or path == "/index.html":
                return self._file("index.html", "text/html")
            if path == "/logs":
                return self._file("logs.html", "text/html")
            if path == "/solicitacoes":
                return self._file("solicitacoes.html", "text/html")
            if path == "/style.css":
                return self._file("style.css", "text/css")
            if path == "/app.js":
                return self._file("app.js", "application/javascript")
            if path == "/api/stats":
                return self._json(self._stats())
            if path == "/api/logs":
                return self._json(self._logs.recent(50))
            if path == "/api/solicitacoes":
                return self._json(self._request_service.listar_pendentes())
            if path == "/api/ping":
                return self._json({"ok": True})

        elif method == "POST":
            if path == "/api/solicitacoes/aprovar":
                ok = await self._request_service.aprovar(self._parse_id(body))
                return self._json({"ok": ok})
            if path == "/api/solicitacoes/negar":
                ok = self._request_service.negar(self._parse_id(body))
                return self._json({"ok": ok})

        return self._not_found()

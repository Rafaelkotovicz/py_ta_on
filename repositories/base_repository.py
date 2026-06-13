"""Repositorio base: abstrai leitura/escrita de uma colecao JSON.

Principios de memoria para o ESP32:
- O arquivo e SEMPRE aberto, lido/gravado e fechado na mesma operacao
  (nada de file handles abertos retidos).
- Nenhuma lista e mantida como atributo: o estado vive no arquivo, nao
  na RAM. Quem precisa de dados pede e descarta.
- `gc.collect()` apos a escrita libera os dicionarios temporarios.
"""

import json
import gc


class BaseRepository:
    """Operacoes genericas sobre uma colecao JSON (lista de objetos)."""

    def __init__(self, path):
        self._path = path

    def _read_raw(self):
        """Le a lista crua do disco. Retorna [] se o arquivo nao existir."""
        try:
            f = open(self._path, "r")
        except OSError:
            return []
        try:
            data = json.load(f)
        except (ValueError, OSError):
            data = []
        finally:
            f.close()
        if not isinstance(data, list):
            return []
        return data

    def _write_raw(self, data):
        """Grava a lista no disco e coleta lixo logo em seguida."""
        f = open(self._path, "w")
        try:
            json.dump(data, f)
        finally:
            f.close()
        gc.collect()

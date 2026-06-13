"""Repositorio de usuarios.

`find_by_uid` percorre o arquivo e retorna assim que encontra, sem manter
a colecao inteira convertida em objetos na RAM.
"""

from repositories.base_repository import BaseRepository
from core.models import Usuario


class UserRepository(BaseRepository):

    def find_by_uid(self, uid):
        """Retorna um Usuario ou None. Itera sem reter a lista completa."""
        for d in self._read_raw():
            if d.get("uid") == uid:
                return Usuario.from_dict(d)
        return None

    def count(self):
        """Total de usuarios cadastrados (sem instanciar objetos)."""
        return len(self._read_raw())

    def all(self):
        """Lista de Usuario. Use com parcimonia (instancia tudo)."""
        return [Usuario.from_dict(d) for d in self._read_raw()]

    def save(self, usuario):
        """Insere ou atualiza um usuario pelo UID."""
        data = self._read_raw()
        for i, d in enumerate(data):
            if d.get("uid") == usuario.uid:
                data[i] = usuario.to_dict()
                self._write_raw(data)
                return
        data.append(usuario.to_dict())
        self._write_raw(data)

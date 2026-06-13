"""Wrapper de alto nivel sobre o MFRC522.

Expoe apenas `read_uid()`, isolando o restante do sistema dos detalhes
do driver (Dependency Inversion: os services dependem desta abstracao,
nao do registrador SPI).
"""

from hardware.mfrc522 import MFRC522


class NFCReader:

    def __init__(self, sck, mosi, miso, rst, cs, spi_id=2, baudrate=1000000):
        self._rdr = MFRC522(sck, mosi, miso, rst, cs, spi_id, baudrate)

    def read_uid(self):
        """Retorna o UID como string hexadecimal (ex.: 'a1b2c3d4') ou None."""
        stat, _ = self._rdr.request(self._rdr.REQIDL)
        if stat != self._rdr.OK:
            return None
        stat, raw = self._rdr.anticoll()
        if stat != self._rdr.OK or len(raw) < 4:
            return None
        return "%02x%02x%02x%02x" % (raw[0], raw[1], raw[2], raw[3])

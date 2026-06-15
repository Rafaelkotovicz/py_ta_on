"""Wrapper de alto nivel sobre o MFRC522.

Expoe apenas `read_uid()`, isolando o restante do sistema dos detalhes
do driver (Dependency Inversion: os services dependem desta abstracao,
nao do registrador SPI).
"""

from machine import Pin, SPI, SoftSPI
import time

from hardware.mfrc522 import MFRC522


class NFCReader:

    def __init__(self, sck, mosi, miso, rst, cs, spi_id=2, baudrate=2500000):
        self._rdr = self._open_reader(sck, mosi, miso, rst, cs, spi_id, baudrate)

    def _open_reader(self, sck, mosi, miso, rst, cs, spi_id, baudrate):
        try:
            SPI(spi_id).deinit()
        except OSError:
            pass

        # 1) VSPI hardware (padrao ESP32: 18/23/19) — mesmo metodo do Wokwi
        spi = SPI(spi_id, baudrate=baudrate, polarity=0, phase=0)
        spi.init()
        rdr = MFRC522(spi, cs, rst)
        ver = rdr._rreg(0x37)
        if ver in (0x91, 0x92):
            return rdr

        # 2) fallback: SoftSPI bit-bang nos mesmos pinos
        try:
            SPI(spi_id).deinit()
        except OSError:
            pass
        soft = SoftSPI(baudrate=baudrate, polarity=0, phase=0,
                       sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
        rdr = MFRC522(soft, cs, rst)
        return rdr

    def read_uid(self):
        """Retorna o UID como string hexadecimal (ex.: 'a1b2c3d4') ou None."""
        stat, _ = self._rdr.request(self._rdr.REQIDL)
        if stat != self._rdr.OK:
            return None
        stat, raw = self._rdr.anticoll()
        if stat != self._rdr.OK or len(raw) < 4:
            return None
        return "%02x%02x%02x%02x" % (raw[0], raw[1], raw[2], raw[3])

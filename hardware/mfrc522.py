"""Driver enxuto para o leitor RFID/NFC MFRC522 (SPI).

Versao reduzida do driver classico de MicroPython (W. Schoonderbeek /
wendlers): mantemos apenas o necessario para detectar a tag e obter o
UID (request + anticoll). Operacoes de autenticacao/leitura de blocos
foram omitidas para economizar flash e RAM, pois o controle de acesso
usa somente o UID.
"""

from machine import Pin, SPI


class MFRC522:

    OK = 0
    NOTAGERR = 1
    ERR = 2

    REQIDL = 0x26
    REQALL = 0x52

    def __init__(self, sck, mosi, miso=None, rst=None, cs=None,
                 spi_id=2, baudrate=1000000):
        # Estilo wendlers: MFRC522(spi, cs, rst) — SPI ja criado externamente
        if isinstance(sck, SPI):
            self.spi = sck
            self.rst = Pin(mosi, Pin.OUT)
            self.cs = Pin(miso, Pin.OUT)
            self.rst.value(0)
            self.cs.value(1)
            self.rst.value(1)
            self.init()
            return

        self.sck = Pin(sck, Pin.OUT)
        self.mosi = Pin(mosi, Pin.OUT)
        self.miso = Pin(miso, Pin.IN)
        self.rst = Pin(rst, Pin.OUT)
        self.cs = Pin(cs, Pin.OUT)

        self.rst.value(0)
        self.cs.value(1)

        self.spi = SPI(spi_id, baudrate=baudrate, polarity=0, phase=0,
                       sck=self.sck, mosi=self.mosi, miso=self.miso)

        self.rst.value(1)
        self.init()

    # ----------------- acesso de baixo nivel -----------------
    def _wreg(self, reg, val):
        self.cs.value(0)
        self.spi.write(b"%c" % int(0xFF & ((reg << 1) & 0x7E)))
        self.spi.write(b"%c" % int(0xFF & val))
        self.cs.value(1)

    def _rreg(self, reg):
        self.cs.value(0)
        self.spi.write(b"%c" % int(0xFF & (((reg << 1) & 0x7E) | 0x80)))
        val = self.spi.read(1, 0xFF)
        self.cs.value(1)
        return val[0]

    def _sflags(self, reg, mask):
        self._wreg(reg, self._rreg(reg) | mask)

    def _cflags(self, reg, mask):
        self._wreg(reg, self._rreg(reg) & (~mask))

    def _tocard(self, cmd, send):
        recv = []
        bits = irq_en = wait_irq = n = 0
        stat = self.ERR

        if cmd == 0x0E:        # MFAuthent
            irq_en = 0x12
            wait_irq = 0x10
        elif cmd == 0x0C:      # Transceive
            irq_en = 0x77
            wait_irq = 0x30

        self._wreg(0x02, irq_en | 0x80)
        self._cflags(0x04, 0x80)
        self._sflags(0x0A, 0x80)
        self._wreg(0x01, 0x00)

        for c in send:
            self._wreg(0x09, c)
        self._wreg(0x01, cmd)

        if cmd == 0x0C:
            self._sflags(0x0D, 0x80)

        i = 2000
        while True:
            n = self._rreg(0x04)
            i -= 1
            if ~((i != 0) and ~(n & 0x01) and ~(n & wait_irq)):
                break

        self._cflags(0x0D, 0x80)

        if i:
            if (self._rreg(0x06) & 0x1B) == 0x00:
                stat = self.OK
                if n & irq_en & 0x01:
                    stat = self.NOTAGERR
                elif cmd == 0x0C:
                    n = self._rreg(0x0A)
                    lbits = self._rreg(0x0C) & 0x07
                    if lbits != 0:
                        bits = (n - 1) * 8 + lbits
                    else:
                        bits = n * 8
                    if n == 0:
                        n = 1
                    elif n > 16:
                        n = 16
                    for _ in range(n):
                        recv.append(self._rreg(0x09))
            else:
                stat = self.ERR

        return stat, recv, bits

    # ----------------- API publica usada -----------------
    def init(self):
        self.reset()
        self._wreg(0x2A, 0x8D)
        self._wreg(0x2B, 0x3E)
        self._wreg(0x2D, 30)
        self._wreg(0x2C, 0)
        self._wreg(0x15, 0x40)
        self._wreg(0x11, 0x3D)
        self.antenna_on()

    def reset(self):
        self._wreg(0x01, 0x0F)

    def antenna_on(self, on=True):
        if on and ~(self._rreg(0x14) & 0x03):
            self._sflags(0x14, 0x03)
        else:
            self._cflags(0x14, 0x03)

    def request(self, mode):
        """Detecta presenca de tag. Retorna (status, bits)."""
        self._wreg(0x0D, 0x07)
        (stat, recv, bits) = self._tocard(0x0C, [mode])
        if (stat != self.OK) | (bits != 0x10):
            stat = self.ERR
        return stat, bits

    def anticoll(self):
        """Anti-colisao: retorna (status, uid[5 bytes])."""
        ser_chk = 0
        ser = [0x93, 0x20]
        self._wreg(0x0D, 0x00)
        (stat, recv, bits) = self._tocard(0x0C, ser)
        if stat == self.OK:
            if len(recv) == 5:
                for i in range(4):
                    ser_chk = ser_chk ^ recv[i]
                if ser_chk != recv[4]:
                    stat = self.ERR
            else:
                stat = self.ERR
        return stat, recv

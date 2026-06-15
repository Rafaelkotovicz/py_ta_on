"""SmartGate ESP32 - ponto de entrada (Composition Root).

Aqui montamos a arvore de dependencias (DI manual) e iniciamos UM unico
event loop uasyncio coordenando tres tarefas cooperativas:
  1) leitura NFC,
  2) leitura dos botoes (senha fisica),
  3) servidor web do dashboard.

Sem threads, sem servidor externo: tudo roda no proprio ESP32.
"""

import uasyncio as asyncio
import network
import time
import gc

from core.config import Config

from repositories.user_repository import UserRepository
from repositories.log_repository import LogRepository
from repositories.request_repository import RequestRepository

from hardware.relay_controller import RelayController
from hardware.button_password import PasswordController

from services.access_strategy import build_strategies
from services.access_service import AccessService
from services.request_service import RequestService

from web.router import Router
from web.server import WebServer


# ----------------------- Infra de rede -----------------------
def _ativar_wlan(wlan):
    """Ativa uma interface Wi-Fi, reiniciando se o driver estiver inconsistente."""
    try:
        wlan.active(True)
        return
    except OSError:
        pass
    wlan.active(False)
    time.sleep_ms(500)
    wlan.active(True)


def _subir_ap(ap, desligar_sta=False):
    """Sobe o Access Point SmartGate."""
    if desligar_sta:
        try:
            network.WLAN(network.STA_IF).active(False)
        except OSError:
            pass
        time.sleep_ms(300)
    if not ap.active():
        ap.active(True)
    ap.config(
        essid=Config.AP_SSID,
        password=Config.AP_PASSWORD,
        authmode=network.AUTH_WPA_WPA2_PSK,
    )
    ap.ifconfig(("192.168.4.1", "255.255.255.0", "192.168.4.1", "8.8.8.8"))
    try:
        ap.config(pm=network.WLAN.PM_NONE)
    except Exception:
        pass
    ip = ap.ifconfig()[0]
    print("Access Point ativo:", Config.AP_SSID, "->", ip)
    return ip


def conectar_wifi():
    """Sobe apenas o AP SmartGate."""
    ap = network.WLAN(network.AP_IF)
    return _subir_ap(ap, desligar_sta=True)


def _ap_ok(ap):
    try:
        return ap.active() and ap.ifconfig()[0] == "192.168.4.1"
    except Exception:
        return False


async def task_wifi_watchdog():
    """Restaura o AP se cair (sem derrubar clientes desnecessariamente)."""
    ap = network.WLAN(network.AP_IF)
    await asyncio.sleep(30)
    while True:
        try:
            if not _ap_ok(ap):
                print("AP caiu - restaurando SmartGate...")
                _subir_ap(ap, desligar_sta=False)
        except Exception as e:
            print("Watchdog WiFi:", e)
        await asyncio.sleep(30)


def sincronizar_relogio():
    """Sincroniza o RTC via NTP (somente com internet na STA)."""
    if not Config.NTP_SYNC or not Config.WIFI_STA_ENABLE:
        return
    try:
        import ntptime
        ntptime.settime()
        print("Relogio NTP sincronizado (UTC)")
    except Exception as e:
        print("Falha ao sincronizar NTP:", e)


# ----------------------- Tarefas assincronas -----------------------
async def task_nfc(access):
    """Inicia NFC apos Wi-Fi estabilizar; le tags com cooldown."""
    await asyncio.sleep(3)
    nfc = None
    try:
        from hardware.nfc_reader import NFCReader
        nfc = NFCReader(Config.PIN_SCK, Config.PIN_MOSI, Config.PIN_MISO,
                        Config.PIN_RST, Config.PIN_SDA, Config.SPI_ID,
                        Config.SPI_BAUDRATE)
        ver = nfc._rdr._rreg(0x37)
        spi_tipo = type(nfc._rdr.spi).__name__
        if ver in (0x91, 0x92):
            print("MFRC522 OK via", spi_tipo, "versao:", hex(ver))
        else:
            print("MFRC522 sem resposta (SPI:", spi_tipo,
                  "versao:", hex(ver), "esperado: 0x91/0x92)")
    except Exception as e:
        print("MFRC522 indisponivel:", e)
        return

    ultimo_uid = None
    ultimo_ms = 0
    while True:
        uid = None
        try:
            uid = nfc.read_uid()
        except Exception:
            uid = None
        if uid:
            agora = time.ticks_ms()
            repetida = (uid == ultimo_uid and
                        time.ticks_diff(agora, ultimo_ms) <
                        Config.NFC_SAME_UID_COOLDOWN_MS)
            if not repetida:
                ultimo_uid = uid
                ultimo_ms = agora
                print("UID lido:", uid)
                try:
                    resultado = await access.handle_nfc(uid)
                    print("Acesso:", resultado)
                except Exception as e:
                    print("Erro NFC:", e)
                    access._relay.fechar()
                gc.collect()
        await asyncio.sleep_ms(Config.NFC_POLL_MS)


async def task_botoes(senha, access):
    """Polling dos botoes; valida senha no event loop."""
    pendente = None

    def capturar(seq):
        nonlocal pendente
        pendente = seq

    senha._on_sequence = capturar

    while True:
        try:
            senha.poll()
            if pendente is not None:
                seq = pendente
                pendente = None
                await access.handle_pin_sequence(seq)
        except Exception as e:
            print("Erro botoes:", e)
        await asyncio.sleep_ms(Config.BUTTON_POLL_MS)


async def task_gc():
    """Coleta de lixo periodica para manter o heap saudavel."""
    while True:
        gc.collect()
        await asyncio.sleep(30)


# ----------------------- Composition Root -----------------------
async def main():
    ip = conectar_wifi()
    sincronizar_relogio()
    gc.collect()

    # Repositorios (persistencia JSON)
    user_repo = UserRepository(Config.PATH_USUARIOS)
    log_repo = LogRepository(Config.PATH_LOGS, Config.MAX_LOGS,
                            Config.PATH_LOG_STATS)
    request_repo = RequestRepository(Config.PATH_SOLICITACOES)

    # Hardware
    relay = RelayController(Config.PIN_RELAY, Config.RELAY_ACTIVE_HIGH,
                            Config.RELAY_OPEN_TIME, Config.RELAY_USE_PULLUP_OFF)
    # So garante repouso (solenoide sem corrente) — sem pulso no boot
    relay.fechar()

    # Services
    request_service = RequestService(request_repo, log_repo, relay, Config)
    strategies = build_strategies(Config.TIME_RESTRICTED_START,
                                  Config.TIME_RESTRICTED_END)
    access = AccessService(user_repo, log_repo, request_service, relay,
                           strategies, Config)

    senha = PasswordController(
        Config.PINS_BUTTON_A, Config.PINS_BUTTON_B,
        Config.BUTTON_ACTIVE_LOW, Config.BUTTON_DEBOUNCE_MS,
        Config.SENHA_TIMEOUT_MS,
    )
    access.bind_pin_input(senha)

    # Web sobe antes do NFC (SPI) para o AP nao cair no boot
    router = Router(user_repo, log_repo, request_repo, request_service)
    server = WebServer(router, Config.WEB_HOST, Config.WEB_PORT)
    await server.start()
    print("Dashboard disponivel em: http://%s/" % ip)
    await asyncio.sleep_ms(500)

    asyncio.create_task(task_nfc(access))
    asyncio.create_task(task_botoes(senha, access))
    asyncio.create_task(relay.watchdog())
    asyncio.create_task(task_wifi_watchdog())
    asyncio.create_task(task_gc())

    # mantem o event loop vivo
    while True:
        await asyncio.sleep(3600)


try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()

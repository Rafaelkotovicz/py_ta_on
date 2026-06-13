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
def conectar_wifi():
    """Tenta o modo estacao; em falha, sobe um Access Point de fallback."""
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        sta.connect(Config.WIFI_SSID, Config.WIFI_PASSWORD)
        t0 = time.time()
        while not sta.isconnected():
            if time.time() - t0 > Config.WIFI_TIMEOUT:
                break
            time.sleep(0.3)
    if sta.isconnected():
        ip = sta.ifconfig()[0]
        print("WiFi conectado:", ip)
        return ip
    if Config.AP_FALLBACK:
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid=Config.AP_SSID, password=Config.AP_PASSWORD)
        ip = ap.ifconfig()[0]
        print("Access Point ativo:", Config.AP_SSID, "->", ip)
        return ip
    return "0.0.0.0"


def sincronizar_relogio():
    """Sincroniza o RTC via NTP (UTC). O fuso e aplicado em core.utils."""
    if not Config.NTP_SYNC:
        return
    try:
        import ntptime
        ntptime.settime()
        print("Relogio NTP sincronizado (UTC)")
    except Exception as e:
        print("Falha ao sincronizar NTP:", e)


# ----------------------- Tarefas assincronas -----------------------
async def task_nfc(nfc, access):
    """Le tags continuamente, com cooldown para nao reprocessar a mesma tag."""
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
                try:
                    await access.handle_nfc(uid)
                except Exception as e:
                    print("Erro NFC:", e)
                gc.collect()
        await asyncio.sleep_ms(Config.NFC_POLL_MS)


async def task_botoes(senha):
    """Faz o polling cooperativo dos botoes da senha fisica."""
    while True:
        try:
            senha.poll()
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
    log_repo = LogRepository(Config.PATH_LOGS, Config.MAX_LOGS)
    request_repo = RequestRepository(Config.PATH_SOLICITACOES)

    # Hardware
    relay = RelayController(Config.PIN_RELAY, Config.RELAY_ACTIVE_HIGH,
                            Config.RELAY_OPEN_TIME)

    # Services
    request_service = RequestService(request_repo, log_repo, relay, Config)
    strategies = build_strategies(Config.TIME_RESTRICTED_START,
                                  Config.TIME_RESTRICTED_END)
    access = AccessService(user_repo, log_repo, request_service, relay,
                           strategies, Config)

    # Leitor NFC (defensivo: se o modulo nao estiver ligado, o web segue ativo)
    nfc = None
    try:
        from hardware.nfc_reader import NFCReader
        nfc = NFCReader(Config.PIN_SCK, Config.PIN_MOSI, Config.PIN_MISO,
                        Config.PIN_RST, Config.PIN_SDA, Config.SPI_ID,
                        Config.SPI_BAUDRATE)
        print("MFRC522 inicializado")
    except Exception as e:
        print("MFRC522 indisponivel:", e)

    # Senha fisica: callbacks agendam o tratamento assincrono
    def on_ok():
        asyncio.create_task(access.handle_password(True))

    def on_fail():
        asyncio.create_task(access.handle_password(False))

    senha = PasswordController(
        Config.PIN_BUTTON_A, Config.PIN_BUTTON_B, Config.SENHA_PADRAO,
        Config.BUTTON_ACTIVE_LOW, Config.BUTTON_DEBOUNCE_MS,
        Config.SENHA_TIMEOUT_MS, on_ok, on_fail,
    )

    # Web
    router = Router(user_repo, log_repo, request_repo, request_service)
    server = WebServer(router, Config.WEB_HOST, Config.WEB_PORT)
    await server.start()
    print("Dashboard disponivel em: http://%s/" % ip)

    # Tarefas cooperativas
    if nfc is not None:
        asyncio.create_task(task_nfc(nfc, access))
    asyncio.create_task(task_botoes(senha))
    asyncio.create_task(task_gc())

    # mantem o event loop vivo
    while True:
        await asyncio.sleep(3600)


try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()

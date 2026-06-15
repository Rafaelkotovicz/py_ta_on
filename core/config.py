"""Configuracao central do SmartGate.

Mantemos tudo como constantes de classe (sem instancias) para que os
valores fiquem no flash e nao gerem objetos extras na RAM do ESP32.
Ajuste os pinos/credenciais conforme o seu hardware antes do deploy.
"""


class Config:
    # ---------------- Wi-Fi (modo estacao) ----------------
    WIFI_SSID = "paitaon"
    WIFI_PASSWORD = "rafaeldecalcinha"
    WIFI_TIMEOUT = 15  # segundos para conectar antes do fallback

    # ---------------- Access Point (fallback) -------------
    AP_FALLBACK = True
    AP_SSID = "SmartGate"
    AP_PASSWORD = "smartgate123"  # >= 8 caracteres

    # ---------------- Servidor Web ------------------------
    WEB_HOST = "0.0.0.0"
    WEB_PORT = 80

    # ---------------- MFRC522 (barramento SPI/VSPI) -------
    SPI_ID = 2          # VSPI no ESP32
    PIN_SCK = 18
    PIN_MOSI = 23
    PIN_MISO = 19
    PIN_RST = 22
    PIN_SDA = 5         # CS / SS do MFRC522 (conforme circuito Wokwi)
    SPI_BAUDRATE = 1000000  # 1 MHz (estavel no Wokwi; ate ~2.5 MHz costuma funcionar)

    # ---------------- Rele / Solenoide --------------------
    PIN_RELAY = 15
    RELAY_ACTIVE_HIGH = True   # True: HIGH aciona; False: modulo ativo-baixo
    RELAY_OPEN_TIME = 5        # segundos de abertura temporaria

    # ---------------- Botoes (senha fisica) ---------------
    PIN_BUTTON_A = 32   # Botao A -> digito '0'
    PIN_BUTTON_B = 33   # Botao B -> digito '1'
    BUTTON_ACTIVE_LOW = True   # com PULL_UP, pressionar = nivel baixo
    BUTTON_DEBOUNCE_MS = 200
    SENHA_PADRAO = "0101"
    SENHA_TIMEOUT_MS = 8000    # reseta a sequencia apos inatividade

    # ---------------- Regra TIME_RESTRICTED ---------------
    TIME_RESTRICTED_START = 12  # 12:00 inclusive
    TIME_RESTRICTED_END = 18    # 18:00 exclusive

    # ---------------- Relogio / NTP -----------------------
    NTP_SYNC = True
    TIMEZONE_OFFSET = -3   # horas em relacao ao UTC (Brasil = -3)

    # ---------------- Repositorios (JSON) -----------------
    PATH_USUARIOS = "data/usuarios.json"
    PATH_LOGS = "data/logs.json"
    PATH_SOLICITACOES = "data/solicitacoes.json"
    MAX_LOGS = 100  # rotacao: limita RAM/flash ocupados pelos logs

    # ---------------- Loops assincronos -------------------
    NFC_POLL_MS = 250
    NFC_SAME_UID_COOLDOWN_MS = 2500  # ignora releitura da mesma tag
    BUTTON_POLL_MS = 40

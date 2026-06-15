"""Configuracao central do SmartGate.

Mantemos tudo como constantes de classe (sem instancias) para que os
valores fiquem no flash e nao gerem objetos extras na RAM do ESP32.
Ajuste os pinos/credenciais conforme o seu hardware antes do deploy.
"""


class Config:
    # ---------------- Wi-Fi (modo estacao) ----------------
    WIFI_STA_ENABLE = False    # True = tenta rede paitaon (pode ocultar o AP)
    WIFI_SSID = "paitaon"
    WIFI_PASSWORD = "rafaeldecalcinha"
    WIFI_TIMEOUT = 10  # segundos para conectar antes de desistir

    # ---------------- Access Point (sempre ligado) --------
    AP_ALWAYS = True
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
    SPI_BAUDRATE = 2500000  # 2.5 MHz (mesmo valor do projeto Wokwi)

    # ---------------- Rele / Solenoide --------------------
    PIN_RELAY = 15
    # Ativo-baixo (IN LOW liga). OBRIGATORIO: resistor 10k entre IN e VCC (5V).
    # Repouso: GPIO em INPUT (IN sobe para 5V via 10k) = rele DESLIGA.
    # Sem o 10k o ESP32 (3.3V) nao desliga o rele 5V -> 2 LEDs sempre acesos.
    RELAY_ACTIVE_HIGH = False
    RELAY_USE_PULLUP_OFF = True
    RELAY_OPEN_TIME = 2

    # Botoes: aceita 32/33 (antigo) e 25/26 (novo) — um par ligado basta
    PINS_BUTTON_A = (32, 25, 4)   # qualquer um -> digito 0
    PINS_BUTTON_B = (33, 26, 27)   # qualquer um -> digito 1
    BUTTON_ACTIVE_LOW = True
    BUTTON_DEBOUNCE_MS = 80
    SENHA_TIMEOUT_MS = 10000
    PIN_SESSION_TIMEOUT_MS = 45000

    # ---------------- Regra TIME_RESTRICTED ---------------
    TIME_RESTRICTED_START = 8   # 08:00 inclusive (horario comercial)
    TIME_RESTRICTED_END = 18    # 18:00 exclusive

    # ---------------- Relogio / NTP -----------------------
    NTP_SYNC = False           # True so com WIFI_STA_ENABLE (AP nao tem internet)
    TIMEZONE_OFFSET = -3   # horas em relacao ao UTC (Brasil = -3)

    # ---------------- Repositorios (JSON) -----------------
    PATH_USUARIOS = "data/usuarios.json"
    PATH_LOGS = "data/logs.json"
    PATH_LOG_STATS = "data/log_stats.json"
    PATH_SOLICITACOES = "data/solicitacoes.json"
    MAX_LOGS = 100  # rotacao da LISTA (FIFO); contadores em log_stats.json

    # ---------------- Loops assincronos -------------------
    NFC_POLL_MS = 250
    NFC_SAME_UID_COOLDOWN_MS = 4000
    BUTTON_POLL_MS = 40

# SmartGate ESP32

Fechadura eletronica inteligente **100% embarcada** em ESP32 com MicroPython.
Le tags NFC (MFRC522), valida permissoes por nivel de acesso, aciona um rele
(solenoide), aceita uma **senha fisica de dois botoes**, registra logs e expoe
um **dashboard web** servido pelo proprio ESP32. Sem Flask, sem banco de dados,
sem servidor externo.

---

## Sumario

- [Visao geral](#visao-geral)
- [Arquitetura](#arquitetura)
- [UML](#uml)
- [Fluxo de autenticacao](#fluxo-de-autenticacao)
- [Fluxo NFC](#fluxo-nfc)
- [Fluxo da senha fisica](#fluxo-da-senha-fisica)
- [Estrutura de pastas](#estrutura-de-pastas)
- [Instalacao do MicroPython](#instalacao-do-micropython)
- [Pinagem](#pinagem)
- [Como acessar o dashboard](#como-acessar-o-dashboard)
- [Niveis de acesso e regras](#niveis-de-acesso-e-regras)
- [Decisoes de otimizacao para o ESP32](#decisoes-de-otimizacao-para-o-esp32)

---

## Visao geral

O ESP32 executa tudo localmente sobre um unico event loop `uasyncio`:

- **Leitura NFC** (MFRC522 via SPI) -> busca o usuario -> aplica a regra do
  nivel -> aciona o rele / cria solicitacao -> registra log.
- **Senha fisica**: Botao A = `0`, Botao B = `1`. Senha padrao `0101`.
- **Servidor HTTP** proprio com dashboard, pagina de logs e de solicitacoes.
- **Persistencia em JSON** (usuarios, logs, solicitacoes) via Repository Pattern.

Bibliotecas usadas: apenas `socket`/`uasyncio`, `machine`, `network`, `json`,
`time`, `gc` (e `ntptime` opcional).

---

## Arquitetura

Projeto em camadas, orientado a objetos, seguindo SOLID, Repository Pattern e
Service Layer. Regras de negocio ficam isoladas em classes.

```
+-------------------------------------------------------------+
|                         main.py                             |
|        (Composition Root + event loop uasyncio)             |
+----------------------+--------------------------------------+
                       |
       +---------------+----------------+----------------------+
       v               v                v                      v
  task_nfc        task_botoes       WebServer              task_gc
       |               |                |
       v               v                v
+--------------------------------------------------------------+
|                       Services (regras)                      |
|  AccessService  RequestService   AccessStrategy(poly)        |
+--------------------------------------------------------------+
       |                                   |
       v                                   v
+----------------------+        +-------------------------------+
|      Hardware        |        |        Repositories           |
| NFCReader/MFRC522    |        | User / Log / Request (JSON)   |
| RelayController      |        +-------------------------------+
| PasswordController   |                    |
+----------------------+                    v
                                     data/*.json
```

**Principios aplicados**

- **Encapsulamento**: cada classe esconde seus detalhes (driver SPI, I/O de
  arquivo, pinos).
- **Heranca + Polimorfismo + Abstracao**: `AccessStrategy` define o contrato
  `avaliar()`; `Admin/User/TimeRestricted/Visitor` o especializam.
- **SOLID**:
  - *SRP*: cada classe tem uma responsabilidade (ex.: `PasswordController` so
    cuida da senha).
  - *OCP*: novo nivel de acesso = nova estrategia, sem alterar `AccessService`.
  - *DIP*: services dependem de abstracoes injetadas (repos, rele, strategies).
- **Repository Pattern**: leitura/escrita JSON isolada dos services.
- **Service Layer**: `AccessService`/`RequestService` orquestram o dominio.

---

## UML

Diagrama de classes simplificado:

```
            <<abstract>>
           AccessStrategy
           + avaliar(usuario, offset)
                  ^
   +------+-------+--------------+--------------+
   |      |                      |              |
Admin   User           TimeRestricted        Visitor
Strategy Strategy        Strategy            Strategy

AccessService o--> UserRepository
AccessService o--> LogRepository
AccessService o--> RequestService
AccessService o--> RelayController
AccessService o--> {AccessStrategy}   (mapa nivel -> estrategia)

RequestService o--> RequestRepository
RequestService o--> LogRepository
RequestService o--> RelayController

BaseRepository <|-- UserRepository
BaseRepository <|-- LogRepository
BaseRepository <|-- RequestRepository

NFCReader o--> MFRC522
Router    o--> (repos + RequestService)
WebServer o--> Router

Usuario { uid, nivel_acesso, ativo, nome }
Log     { uid, data_hora, metodo, nivel_acesso, resultado }
Solicitacao { id, uid, data_hora, status }
```

---

## Fluxo de autenticacao

```
Evento (NFC ou Senha)
        |
        v
   AccessService
        |
   +----+-----------------------------+
   | NFC: busca Usuario por UID        |
   | Senha: valida sequencia 0101      |
   +----+-----------------------------+
        |
        v
  Estrategia.avaliar() -> LIBERADO | NEGADO | PENDENTE
        |
        +-- LIBERADO  -> RelayController.liberar_temporariamente() + Log
        +-- PENDENTE  -> RequestService.criar() (solicitacao) + Log
        +-- NEGADO    -> Log
        |
        v
   Dashboard reflete via polling (/api/...)
```

## Fluxo NFC

1. `task_nfc` chama `NFCReader.read_uid()` (request + anticoll no MFRC522).
2. Cooldown evita reprocessar a mesma tag repetidamente.
3. `AccessService.handle_nfc(uid)`:
   - busca o `Usuario` (`UserRepository`);
   - se inexistente/inativo -> log **NEGADO**;
   - senao, aplica `AccessStrategy` do nivel;
   - **LIBERADO** -> aciona rele; **PENDENTE** -> cria solicitacao;
     **NEGADO** -> apenas log.
4. `gc.collect()` apos cada leitura.

## Fluxo da senha fisica

1. `task_botoes` chama `PasswordController.poll()` (deteccao de borda +
   debounce, sem IRQ).
2. Botao A acrescenta `0`, Botao B acrescenta `1`.
3. Ao atingir o tamanho da senha, valida contra `0101`:
   - correta -> callback `on_ok` -> `handle_password(True)` -> rele + log
     **LIBERADO** (metodo `SENHA`);
   - errada -> `on_fail` -> log **NEGADO**.
4. Sequencia tambem reseta apos `SENHA_TIMEOUT_MS` de inatividade.

---

## Estrutura de pastas

```
paitus/
├── main.py                      # Composition Root + event loop
├── core/
│   ├── config.py                # pinos, tempos, wifi, paths
│   ├── enums.py                 # NivelAcesso, Metodo, Resultado, Status
│   ├── models.py                # Usuario, Log, Solicitacao
│   └── utils.py                 # relogio com fuso
├── hardware/
│   ├── mfrc522.py               # driver SPI enxuto (so UID)
│   ├── nfc_reader.py            # wrapper read_uid()
│   ├── relay_controller.py      # abrir/fechar/liberar_temporariamente
│   └── button_password.py       # senha de dois botoes
├── services/
│   ├── access_strategy.py       # estrategias por nivel (polimorfismo)
│   ├── access_service.py        # orquestra NFC e senha
│   └── request_service.py       # aprovar/negar solicitacoes
├── repositories/
│   ├── base_repository.py       # I/O JSON
│   ├── user_repository.py
│   ├── log_repository.py        # com rotacao (MAX_LOGS)
│   └── request_repository.py
├── web/
│   ├── server.py                # HTTP via uasyncio (streaming)
│   ├── router.py                # rotas estaticas + API JSON
│   └── static/                  # dashboard (HTML/CSS/JS)
│       ├── index.html
│       ├── logs.html
│       ├── solicitacoes.html
│       ├── style.css
│       └── app.js
└── data/
    ├── usuarios.json
    ├── logs.json
    └── solicitacoes.json
```

---

## Instalacao do MicroPython

1. **Instale as ferramentas** (no PC):

```bash
pip install esptool mpremote
```

2. **Grave o firmware** MicroPython para ESP32 (baixe o `.bin` em
   micropython.org/download/esp32):

```bash
esptool.py --chip esp32 --port COM3 erase_flash
esptool.py --chip esp32 --port COM3 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-xxxxxxxx.bin
```

3. **Configure** o Wi-Fi em `core/config.py` (`WIFI_SSID`, `WIFI_PASSWORD`).

4. **Envie o projeto** para o ESP32 (mantendo a estrutura de pastas):

```bash
mpremote connect COM3 fs cp -r core hardware services repositories web data main.py :
```

> Em Linux/Mac troque `COM3` por algo como `/dev/ttyUSB0`.

5. **Reinicie** a placa. O `main.py` roda no boot. Acompanhe o console:

```bash
mpremote connect COM3 repl
```

---

## Pinagem

### ESP32 (resumo)

| Funcao              | GPIO |
|---------------------|------|
| SPI SCK (MFRC522)   | 18   |
| SPI MOSI (MFRC522)  | 23   |
| SPI MISO (MFRC522)  | 19   |
| MFRC522 RST         | 22   |
| MFRC522 SDA/CS      | 21   |
| Rele (IN)           | 25   |
| Botao A (`0`)       | 32   |
| Botao B (`1`)       | 33   |

### MFRC522 (SPI / VSPI)

| MFRC522 | ESP32       |
|---------|-------------|
| SDA/SS  | GPIO 21     |
| SCK     | GPIO 18     |
| MOSI    | GPIO 23     |
| MISO    | GPIO 19     |
| RST     | GPIO 22     |
| 3.3V    | 3V3 (NAO 5V)|
| GND     | GND         |

### Rele

| Rele | ESP32 |
|------|-------|
| IN   | GPIO 25 |
| VCC  | 5V (ou 3V3 conforme o modulo) |
| GND  | GND |

> Ajuste `RELAY_ACTIVE_HIGH` em `config.py` se o seu modulo for ativo-baixo.
> O solenoide deve ter alimentacao propria e diodo de roda-livre.

### Botoes

| Botao | ESP32   | Observacao |
|-------|---------|------------|
| A     | GPIO 32 | outro lado ao GND (usa PULL_UP interno) |
| B     | GPIO 33 | outro lado ao GND (usa PULL_UP interno) |

---

## Como acessar o dashboard

1. Apos o boot, o console imprime o IP, ex.: `Dashboard disponivel em: http://192.168.0.42/`.
2. Abra esse IP no navegador (mesma rede Wi-Fi).
3. Se o Wi-Fi falhar, o ESP32 sobe um Access Point:
   - SSID: `SmartGate` / Senha: `smartgate123`
   - Conecte-se e acesse `http://192.168.4.1/`.

Paginas:
- `/` — Dashboard (usuarios, acessos, negados, pendentes).
- `/logs` — Tabela de logs (atualizacao por polling).
- `/solicitacoes` — Aprovar/Negar pedidos de visitantes.

---

## Niveis de acesso e regras

| Nivel            | Comportamento                                              |
|------------------|-----------------------------------------------------------|
| `ADMIN`          | Abre imediatamente + log.                                  |
| `USER`           | Abre imediatamente + log.                                  |
| `TIME_RESTRICTED`| Abre **somente** entre 12:00 e 18:00; fora -> NEGADO.     |
| `VISITOR`        | Nao abre; gera **solicitacao PENDENTE** para aprovacao.   |

Os UIDs de exemplo estao em `data/usuarios.json` (troque pelos UIDs reais das
suas tags — o console imprime o UID lido).

---

## Decisoes de otimizacao para o ESP32

- **Event loop unico (`uasyncio`)**: evita `_thread` e o overhead de pilhas.
- **Streaming de arquivos** no servidor (chunks de 512 B): paginas HTML/CSS/JS
  nunca sao carregadas inteiras na RAM.
- **Repositorios sem estado**: arquivos abertos, lidos/gravados e fechados na
  hora; nenhuma colecao grande fica retida em memoria.
- **Rotacao de logs** (`MAX_LOGS`): limita o crescimento de `logs.json`.
- **Estrategias singleton**: uma instancia por nivel reutilizada em todo acesso.
- **`__slots__`** nos modelos: reduz o consumo por objeto.
- **`gc.collect()`** apos cada requisicao web, leitura NFC e a cada 30 s.
- **Driver MFRC522 reduzido**: apenas request/anticoll (somente o UID), poupando
  flash e RAM.
- **Polling no front-end** (sem WebSocket): conexoes curtas com `Connection: close`.
```

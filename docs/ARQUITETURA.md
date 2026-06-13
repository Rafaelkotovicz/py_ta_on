# Arquitetura - SmartGate ESP32

Documento de apoio. A visao completa (UML, fluxos, pinagem, instalacao) esta
no `[README.md](../README.md)` na raiz do projeto.

## Camadas


| Camada       | Pasta           | Responsabilidade                                 |
| ------------ | --------------- | ------------------------------------------------ |
| Apresentacao | `web/`          | HTTP assincrono + dashboard (HTML/CSS/JS)        |
| Servicos     | `services/`     | Regras de negocio e orquestracao (Service Layer) |
| Persistencia | `repositories/` | Leitura/escrita JSON (Repository Pattern)        |
| Hardware     | `hardware/`     | MFRC522, rele, botoes (abstracoes de hardware)   |
| Dominio      | `core/`         | Config, enums, modelos, utilitarios              |


## Padroes

- **Strategy** (`services/access_strategy.py`): polimorfismo por nivel de acesso.
- **Repository** (`repositories/`): abstrai a fonte de dados (JSON).
- **Service Layer** (`services/access_service.py`, `request_service.py`).
- **Dependency Injection** manual no `main.py` (Composition Root).

## Regras de acesso (resumo)

- `ADMIN` / `USER`: liberam imediatamente.
- `TIME_RESTRICTED`: libera somente entre 12:00 e 18:00.
- `VISITOR`: gera solicitacao PENDENTE (aprovacao pelo dashboard).


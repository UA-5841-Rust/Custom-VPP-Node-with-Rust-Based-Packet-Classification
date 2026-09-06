# VPP node with Rust packet classification

Навчальний VPP-плагін: нода на C передає Ethernet-кадр у безпечний Rust-парсер
через FFI без копіювання payload. Коректний UDP проходить до Ethernet echo-ноди;
пошкоджені та непідтримувані пакети переходять у `error-drop`.

**Статус:** Rust і Scapy/ABI перевірені у Windows. C-плагін та інтеграційні
VPP-тести написані, але ще потребують збірки й запуску у WSL/Linux.
Деталі: [результати перевірок](docs/validation.md).

## Потік обробки

```text
pg-input / Ethernet device
    → device-input feature: rust-classify-node (C)
        → packet_classify(ptr, current_length) (Rust)
            → safe parse_packet
        → valid UDP: rust-classify-forward → interface-output (той самий порт)
        → invalid/unsupported: error-drop
```

Echo міняє лише Ethernet source/destination MAC місцями. IP-адреси, UDP-порти
й payload не змінюються. Це спосіб побачити, що класифікований пакет дійшов до
наступної ноди; IP-маршрутизація й ARP для цього тесту не потрібні.

## Файли

| Шлях | Призначення |
| --- | --- |
| `src/` | Парсер із task_01 і новий allocation-free FFI |
| `include/network_parser.h` | C ABI та стабільні коди помилок |
| `plugin/` | C-ноди, CLI, feature registration, CMake |
| `tests/*.rs` | Parser, FFI, ABI layout, edge cases, allocation test |
| `tests/test_rust_classify.py` | VppTestCase: трафік, counters, trace, disable |
| `tests/ffi_smoke.c` | Перевірка C → Rust зі статичним лінкуванням |
| `scripts/` | Підключення до VPP, Scapy-сценарії, PCAP, локальні перевірки |

## Запуск

Rust можна перевірити прямо з кореня репозиторію:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo build --release
```

Для VPP дивись [покрокову інструкцію WSL](docs/wsl.md). Після підключення й
збірки плагіна feature вмикається в CLI VPP:

```text
rust classify pg0
rust classify pg0 disable
```

Лічильники у `show errors` та `/err/rust-classify-node/`:

- `forwarded_ok`: коректні UDP, передані наступній ноді;
- `malformed_packet`: структурно некоректні пакети;
- `unsupported_protocol`: EtherType/protocol/fragments або chained buffers;
- `chained_buffer`: додаткова деталізація unsupported;
- `dropped`: загальна кількість відкинутих, яку рахує `error-drop`.

Класифікаційні лічильники оновлюються пакетно, окремо для кожного worker.

## Межі реалізації

- Ethernet II + IPv4 + UDP; без VLAN, IPv6 і reassembly.
- Лише один суцільний VPP segment; chains відкидаються без копіювання.
- Перевіряється структура та довжини, але не checksum чи вміст IP options.
- Немає алокацій у звичайній класифікації. Увімкнений VPP trace може виділяти
  діагностичну пам’ять і не входить до цього твердження.
- Feature завершує input feature path через echo/drop; він призначений для
  окремого тестового інтерфейсу, не для прозорого production routing.
- Сумісність із конкретною збіркою VPP та WSL підтверджуватиметься запуском.

[FFI, ownership та unsafe](docs/ffi-boundary.md) ·
[Походження парсера](docs/provenance.md) ·
[Оригінальне завдання](docs/assignment.md)

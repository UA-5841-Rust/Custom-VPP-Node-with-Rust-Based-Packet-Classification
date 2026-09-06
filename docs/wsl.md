# Перевірка у WSL / Linux

Це наступний етап роботи. Наведені VPP-команди ще не виконані в цьому проєкті.
Ціль для початкової перевірки — VPP `stable/2506`; сумісність потрібно підтвердити
реальною збіркою. Якщо у тебе вже є версія VPP від ментора, спочатку звіримо її,
а не перевстановлюватимемо середовище. WSL2 потрібен для Linux-частини; придатність
його конфігурації до VPP-тестів перевіримо окремо.

## 1. Огляд середовища

У PowerShell: `wsl --list --verbose`. Усередині Ubuntu:

```bash
uname -a
cat /etc/os-release
rustc --version
cargo --version
cc --version
cmake --version
```

Потрібні Linux Rust toolchain, C/C++ toolchain і залежності обраної версії VPP.
Для VPP, зібраного з source, користуйся його `make install-dep` та інструкціями
ментора. Не збирай Cargo/VPP через `sudo`: права можуть бути потрібні для
встановлення залежностей і запуску тестів, але не для компіляції.

Репозиторій у Windows доступний як:

```bash
cd /mnt/c/Users/user/Desktop/RUST/week3/Custom-VPP-Node-with-Rust-Based-Packet-Classification
```

Для тривалих збірок бажано розмістити робочі файли й VPP у Linux-файловій системі.
Перенесення робитимемо окремо, зберігши локальні коміти та поточну гілку. Не
потрібно пушити на GitHub, щоб перенести роботу у WSL. Windows `.lib`/`.dll`
не підходять для Linux-плагіна — Cargo має створити Linux `.a`/`.so`.

## 2. Rust та C ABI

З кореня цього репозиторію:

```bash
bash scripts/check-rust.sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r scripts/requirements.txt
python scripts/check_fixtures.py target/release/libnetwork_parser.so
```

Скрипт перевіряє fmt, Clippy, Rust-тести, release і C-програму, яка викликає
реальний ABI. Python додатково звіряє Scapy-сценарії з бібліотекою та PCAP.

## 3. Підключення до VPP

Приклад, якщо checkout VPP знаходиться у `~/vpp`:

```bash
bash scripts/prepare-vpp.sh ~/vpp
cd ~/vpp
make build
make build-release
```

Скрипт створює два симлінки: плагін у `src/plugins/rust_classify` і тест у `test/`.
Існуючі чужі файли він не перезаписує. CMake сам збирає Linux Rust archive з PIC
в окремій папці VPP build. Не потрібно копіювати `.a` вручну. Для debug VPP Rust
поки теж збирається в release; для покрокового входу в Rust можна окремо змінити
профіль збірки після первинної перевірки.

Після запуску зібраного VPP (наприклад, `make run` для debug) у його CLI:

```text
show plugins
show node rust-classify-node
show node rust-classify-forward
```

На WSL почнемо з packet-generator без фізичної NIC і DPDK. Якщо типовий startup
вимагає недоступні драйвери/hugepages, налаштуємо конфігурацію за фактичним
повідомленням про помилку.

## 4. Автоматизовані тести VPP

У checkout VPP:

```bash
make test TEST=test_rust_classify
make test-debug TEST=test_rust_classify
```

Тести перевіряють точні байти Ethernet echo, відкидання некоректних пакетів,
лічильники, trace, 1100 пакетів за один сценарій і вимкнення feature.
Системне оточення та Python-залежності VPP налаштовує його test framework.
Збережи повний лог і версію `git rev-parse HEAD` VPP як evidence.

## 5. Ручний packet-generator

У цьому репозиторії, з активованим Python venv:

```bash
python scripts/generate_packets.py /tmp/rust-classify-packets
```

У **новому** екземплярі VPP, без уже створеного `pg0`:

```text
exec /tmp/rust-classify-packets/run.cli
show packet-generator
show errors
show trace
show run
```

Дочекайся завершення всіх streams перед звіркою. Очікувані значення після одного
запуску: `forwarded_ok=2`, `unsupported_protocol=4`, `malformed_packet=5`,
`dropped=9`, `chained_buffer=0`. Це очікування, а не вже отримані VPP-результати.
У trace коректного пакета має бути `protocol 1 port 4321 valid 1 error 0`.
Trace вмикаємо на `pg-input`, щоб downstream-нода могла записати свою частину.

## 6. GDB та завершення

```bash
# У цьому репозиторії після check-rust.sh:
gdb --args target/ffi-smoke
# У checkout VPP:
make debug
```

У GDB: `run`, за потреби breakpoint на `packet_classify`. Прожени пошкоджені PCAP
у debug VPP. Порожній ввід, null/zero і всі короткі префікси перевіряє C smoke
test: не створюй некоректний довільний вказівник і не очікуй, що Rust зможе
перевірити доступність чужої пам'яті.

Після проходження перевірок оновимо `docs/validation.md`, додамо справжні логи,
підготуємо опис PR та зробимо один фінальний push за домовленістю.

# VPP Node with Rust Packet Classification

This educational VPP plugin classifies Ethernet II / IPv4 / UDP frames through
an allocation-free Rust FFI function. Valid UDP packets are sent to an Ethernet
echo node; malformed and unsupported packets are sent to `error-drop`.

## Processing flow

```text
pg-input / Ethernet device
    → device-input feature: rust-classify-node (C)
        → packet_classify(ptr, current_length) (Rust)
            → safe parse_packet
        → valid UDP: rust-classify-forward → interface-output
        → invalid/unsupported: error-drop
```

The echo node swaps only the Ethernet source and destination MAC addresses.
IP addresses, UDP ports, and payload remain unchanged. This makes forwarding
observable without requiring IP routing or ARP.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/` | Zero-copy parser and allocation-free Rust FFI |
| `include/network_parser.h` | C ABI and stable error codes |
| `plugin/` | C graph nodes, CLI, feature registration, and CMake |
| `tests/*.rs` | Parser, FFI, ABI, edge-case, and allocation tests |
| `tests/test_rust_classify.py` | VPP integration tests with Scapy |
| `tests/ffi_smoke.c` | Static-link C/Rust ABI smoke test |
| `scripts/` | VPP setup, packet fixtures, PCAP generation, and checks |
| `docs/` | Assignment, WSL setup, FFI safety, provenance, and validation |

## Rust checks

From the repository root:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cargo build --release --locked --offline
```

For Linux/VPP setup, see [the WSL guide](docs/wsl.md). Once the plugin is built,
enable or disable it on a test interface in the VPP CLI:

```text
rust classify pg0
rust classify pg0 disable
```

## Counters

The node exposes these counters through `show errors`:

- `forwarded_ok`: structurally valid UDP frames sent to the next node;
- `malformed_packet`: packets with invalid structure or lengths;
- `unsupported_protocol`: unsupported EtherTypes, IP protocols, fragments, or chains;
- `chained_buffer`: additional detail for non-contiguous VPP buffers;
- `dropped`: total packets sent to `error-drop`.

Classification counters are accumulated per frame and updated on the current
VPP worker.

## Scope and limitations

- Supports Ethernet II, IPv4, and UDP only; VLAN, IPv6, and fragment reassembly are unsupported.
- Only one contiguous VPP buffer segment is classified; chains are rejected without copying.
- Header structure and lengths are checked, but IP/UDP checksums and option contents are not validated.
- Normal classification performs no heap allocation. VPP diagnostic tracing may allocate trace storage.
- The feature consumes the device-input path for the selected test interface and is intended as an educational echo/drop demonstration.
- Performance profiling with `perf` was not performed.

See [FFI ownership and unsafe-code notes](docs/ffi-boundary.md),
[validation results](docs/validation.md),
[parser provenance](docs/provenance.md), and [the original assignment](docs/assignment.md).

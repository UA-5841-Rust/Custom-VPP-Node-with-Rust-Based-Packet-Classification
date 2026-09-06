# Custom VPP Node with Rust-Based Packet Classification

This project implements a custom **Vector Packet Processing (VPP)** graph node that performs zero-copy packet classification (Ethernet / IPv4 / UDP) using a safe **Rust** parsing library across an FFI boundary.

## Solution Architecture

```text
                 Ethernet/IPv4/UDP raw packet (vector of buffers)
                            |
                            v
                 +--------------------------+
                 | VPP graph node (C)       |
                 | rust-classify-node       |
                 |  - vlib_buffer_t access  |
                 |  - batching / vector loop|
                 +--------------------------+
                            |
                     raw ptr + len (no copy)
                            |
                            v
                 +--------------------------+
                 | FFI boundary (unsafe,    |
                 | isolated, validated)     |
                 +--------------------------+
                            |
                            v
                 +--------------------------+
                 | network_parser (Rust)    |
                 | packet_classify(...)     |
                 | -> #[repr(C)] result     |
                 +--------------------------+
                            |
              +-------------+----------------+
              |                              |
              v                              v
     next-node: forward             next-node: error-drop
     (e.g. ip4-lookup /              + increment counter
     your own "passthrough" node)     (malformed / unsupported)
```

> **Key Constraint:** The VPP node itself and its dispatch function remain in C (satisfying VLIB requirements). Rust is exclusively responsible for safe, zero-copy packet parsing via a high-performance FFI boundary.

---

## Repository Structure

* `src/` — Rust-based zero-copy network parser library (`network_parser`) with C FFI bindings.
* `rust_classify/` — The VPP C plugin source code registering the `rust-classify` graph node.
* `test_rust_classify.py` — Python / Scapy functional test case for VPP's `make test` framework.
* `MONITORING.md` — Guide on traffic generation, CLI tracing, and GDB debugging.
* `PERFORMANCE.md` — Performance benchmarks, `show run` metrics, and FFI overhead analysis.

---

## Integration Guide: Moving Files into VPP

To build and run this plugin, it must be placed inside your local VPP source tree.

### 1. Place the Plugin
Copy the `rust_classify` directory into VPP's internal plugins source folder:
```bash
cp -r ./rust_classify /path/to/vpp/src/plugins/rust_classify
```

### 2. Place the Python Test
Copy the integration test file into VPP's test framework directory:
```bash
cp ./test_rust_classify.py /path/to/vpp/test/
```

---

## Building VPP with the Rust Plugin

Because the plugin relies on a compiled Rust static/dynamic library (`cdylib`/`staticlib`/`rlib`), ensure you have `Rust` and `Cargo` installed.

1. **Build the Rust Parser (Release Mode):**
   Navigate to your Rust library directory and compile it with optimizations:
   ```bash
   cd /path/to/network_parser
   cargo build --release
   ```

2. **Build VPP from Source:**
   Navigate to your VPP root directory and trigger the release build. If your CMake build needs to locate external Rust artifacts or header files, pass them via `VPP_EXTRA_CMAKE_ARGS`:
   ```bash
   cd /path/to/vpp
   make build-release VPP_EXTRA_CMAKE_ARGS="-DNETWORK_PARSER_DIR=/path/to/network_parser"
   ```
   *(Note: Adjust CMake arguments depending on network_parser path).*

---

## Running VPP

Once built, you can run VPP in interactive mode (or background daemon mode) using the release binaries:

* **Run VPP (Release):**
  ```bash
  sudo build-root/install-vpp-native/vpp/bin/vpp -c config.cfg
  ```
* **Connect to the VPP Control CLI (`vppctl`):**
  ```bash
  sudo build-root/install-vpp-native/vpp/bin/vppctl
  ```

**The `config.cfg` example:**
```plaintext
unix {
    cli-listen /run/vpp/cli.sock 
    nodaemon
    exec /path/to/vpp/config.cmd
}

plugins {
    plugin dpdk_plugin.so { disable }
    plugin unittest_plugin.so { enable }
    plugin rust_classify.so { enable }
}

socksvr {
    default
}

session {
    enable
}
```

**The `config.cmd` example:**
```plaintext
create tap id 0 host-ip4-addr 192.168.10.2/24
set interface ip address tap0 192.168.10.1/24
set interface state tap0 up
```

---

## Testing & Verification

1. **Functional Tests (`make test`):**
   To execute the Python/Scapy test suite and verify packet forwarding/dropping behavior against expected error counters:
   ```bash
   make test TEST=test_rust_classify VPP_EXTRA_CMAKE_ARGS="-DNETWORK_PARSER_DIR=/path/to/network_parser"
   ```
   *(Note: Adjust CMake arguments depending on network_parser path).*

2. **Manual CLI Traffic Testing & Tracing:**
   Detailed instructions on using `packet-generator`, `trace add`, and `pcap trace` can be found in [TESTING.md](./TESTING.md).

---

## Performance Sanity Check

To evaluate the overhead of crossing the C ↔ Rust FFI boundary, performance benchmarks were conducted under a 50 million packet synthetic stream using VPP's internal CPU cycle counters (`show run`). 

* Detailed methodology, raw results comparing baseline C vs. active FFI, and analysis are documented in [PERFORMANCE.md](./PERFORMANCE.md).

To thoroughly test the Rust parser's edge cases, Python and `scapy` were used to generate a `.pcap` file rather than relying on raw hex strings in the VPP CLI. This approach ensures reproducible, documented test cases and prevents the VPP CLI text parser from auto-correcting intentionally malformed lengths or checksums.

### 1. Testing Using `packet-generator` with Controlled Packet Streams

**Implemented Test Cases:**
1. **Valid Packet:** Standard Ethernet + IPv4 + UDP structure.
2. **IP Options:** An IPv4 packet with options enabled (IHL=6, 24-byte header).
3. **Invalid EtherType:** An ARP packet injected instead of IPv4 to test L2 filtering.
4. **Truncated Payload:** A packet where headers indicate a large UDP length, but the physical payload is truncated.

**Reproduction Steps:**
1. Ensure `python3` and the `scapy` library are installed on the host system.
2. Generate the `traffic.pcap` file using the generator script:
    ```bash
    python3 gen_test_pcap.py
    ```
3. Inject the traffic and verify the processing behavior inside VPP:
    ```plaintext
    vpp# trace add pg-input 10
    vpp# packet-generator new { name pcap_test node rust-classify pcap /path/to/traffic.pcap }
    vpp# packet-generator enable
    vpp# show errors
    vpp# show trace
    ```

**Expected Results:**
* `error_code 0` (Success) for valid packets and packets with IP options.
* `error_code 3` (`INVALID_ETHER_TYPE`) for the ARP packet.
* `error_code 7` (`INVALID_UDP_LENGTH`) for the truncated packet.

The node counters correctly reflected 2 successfully forwarded packets and 2 gracefully dropped packets.

---

### 2. Real-World Traffic Validation

To ensure the Rust FFI boundary is robust against unpredictable live network traffic, the node was evaluated using real network captures containing a diverse mix of background protocols.

1. Capture live traffic via `tcpdump`:
    ```bash
    # Replace interface and path as necessary for your environment
    sudo tcpdump -i eth0 -c 20 -w /path/to/real_traffic.pcap
    ```

2. Inject the captured pcap into VPP:
    ```plaintext
    vpp# trace add pg-input 20
    vpp# packet-generator new { name real_test node rust-classify pcap /path/to/real_traffic.pcap }
    vpp# packet-generator enable
    ```

3. Analyze the runtime classification errors and packet traces:
    ```plaintext
    vpp# show errors
    vpp# show trace
    ```

**Validation Analysis:**
The live packet capture included various background protocols such as `ICMP`, `ARP`, and `IGMP`. The Rust parser successfully categorized all live traffic without triggering a single panic, memory leak, or crash:
* **ARP Requests** were instantly isolated and dropped at the L2 parsing stage with `error_code 3` (`INVALID_ETHER_TYPE`).
* **ICMP (Ping)** and **IGMP (Multicast)** packets were correctly processed up to the IPv4 layer, but were safely dropped with `error_code 8` (`UNSUPPORTED_PROTOCOL`) since they did not match the target UDP protocol (Protocol 17).

---

### 3. Automated VPP Integration Testing (`VppTestCase`)

To align with VPP's native development workflow, an automated integration test was developed using the `VppTestCase` framework and `Scapy`. The test constructs packets covering the core edge cases (valid, IP options, truncated payload, invalid version, and bad header length), injects them via `add_stream`, and asserts that the node's internal statistics counters match the expected outcome.

**Execution Steps:**
Navigate to your VPP root directory and execute the specific test suite while passing the CMAKE arguments for the external dependency:
```bash
cd /path/to/vpp
make test TEST=test_rust_classify VPP_EXTRA_CMAKE_ARGS="-DNETWORK_PARSER_DIR=/path/to/network_parser"
```

**Expected Test Output:**
```plaintext
====================================================================================================
Rust Classify Node Test Case
====================================================================================================
Test rust-classify with valid and malformed packets                                       0.15 OK

====================================================================================================
TEST RESULTS:
    Scheduled tests: 1
     Executed tests: 1
       Passed tests: 1
====================================================================================================

Test run was successful
```

---

### 4. FFI Boundary Crash Resilience Verification (GDB)

To verify firsthand that the FFI boundary does not crash or trigger segmentation faults when presented with severely corrupted or malformed data (e.g., zero-length buffers, empty frames, or payloads shorter than the minimum header size), a runtime debugging session was conducted using GDB under a debug build.

1. Stop any existing VPP processes (`vppctl quit` or `Ctrl+C`) and start VPP in debug mode from your VPP root directory:
    ```bash
    make debug
    ```

2. Set a breakpoint on the graph node's primary C entry function (`rust_classify_node_fn`):
    ```plaintext
    (gdb) break rust_classify_node_fn
    ```

3. Launch the VPP process within the debugger:
    ```plaintext
    (gdb) run
    ```

4. Open a secondary terminal window and connect to the VPP control console to trigger the packet generator using the malformed traffic pcap:
    ```bash
    # Note: Adjust the 'XXX-native' directory name based on your specific build architecture
    sudo ~/vpp/build-root/XXX-native/vpp/bin/vppctl

    vpp# trace add pg-input 10
    vpp# packet-generator new { name pcap_test node rust-classify pcap /path/to/traffic.pcap }
    vpp# packet-generator enable
    ```

5. Step through the execution in the GDB terminal to verify memory safety:
* Use `list` to align with the surrounding C loop logic.
* Use `next` (or `n`) to advance execution until reaching the exact line calling the Rust FFI function (e.g., `parse_packet(...)`).
* Execute `print b0->current_length` to inspect the physical length of the malformed buffer being passed across the boundary.
* Step `next` over the Rust FFI function call. 
* **Memory Safety Validation:** GDB successfully advances to the next C instruction without throwing a `SIGSEGV` (Segmentation Fault), proving that the Rust boundary safely handles unexpected buffer sizes.
* Execute `print error0` to verify that the Rust parser returned the appropriate error code (e.g., `7` for truncated frames) instead of crashing the worker thread.
* Type `continue` (or `c`) to let the graph node finish processing the remaining packet vectors.

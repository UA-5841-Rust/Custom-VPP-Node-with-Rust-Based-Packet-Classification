# Zero-copy network packet parser

This project is a **zero-copy network packet parser** that was created to be used in the VPP custom plugin. It implements a zero-copy Ethernet II / IPv4 / UDP packet parser in Rust, with a safe Rust API and a C-compatible FFI layer.
You can read more about it [here](https://github.com/UA-5841-Rust/zero-copy).

To write a plugin a header had to be created. It's just a contract of `network parser` for our plugin written on **C**. The header was generated and committed to the repository (`include/network_parser.h`).
However, it can be generated as many times as you want - result will be the same.

To generate header use the command below:

```bash
    make generate_header
```

(_Before you try it, make sure you have [cbindgen](https://github.com/mozilla/cbindgen) installed_)

You can test this project using `cargo test` as well as `make test` commands.

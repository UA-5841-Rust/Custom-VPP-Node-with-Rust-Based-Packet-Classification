#include <vnet/vnet.h>
#include <vnet/plugin/plugin.h>
#include <rust_classify/rust_classify.h>

#include <network_parser.h>
#include <vpp/app/version.h>

rust_classify_main_t rust_classify_main;

static clib_error_t *
rust_classify_init (vlib_main_t *vm)
{
	rust_classify_main_t *rmp = &rust_classify_main;
	rmp->vnet_main = vnet_get_main ();

	// linker function
	struct ClassifyResult link_check = packet_classify (0, 0);
	(void) link_check;

	return 0;
}

VLIB_INIT_FUNCTION (rust_classify_init);

/* *INDENT-OFF* */
VLIB_PLUGIN_REGISTER () = {
	.version = VPP_BUILD_VER,
	.description = "Rust-based UDP packet classification node",
};
/* *INDENT-ON* */

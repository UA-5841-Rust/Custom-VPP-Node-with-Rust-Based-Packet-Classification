#include <vlib/vlib.h>
#include <vnet/vnet.h>
#include <vnet/plugin/plugin.h>
#include "network_parser.h"

/* Define next nodes */
typedef enum {
    RUST_CLASSIFY_NEXT_DROP,
    RUST_CLASSIFY_N_NEXT,
} rust_classify_next_t;

/* Main dispatch function for the node */
static uword
rust_classify_node_fn (vlib_main_t * vm,
                       vlib_node_runtime_t * node,
                       vlib_frame_t * frame)
{
    u32 n_left_from, * from, * to_next;
    rust_classify_next_t next_index;

    from = vlib_frame_vector_args (frame);
    n_left_from = frame->n_vectors;
    next_index = node->cached_next_index;

    while (n_left_from > 0)
    {
        u32 n_left_to_next;

        vlib_get_next_frame (vm, node, next_index, to_next, n_left_to_next);

        while (n_left_from > 0 && n_left_to_next > 0)
        {
            u32 bi0;
            vlib_buffer_t * b0;
            u32 next0 = RUST_CLASSIFY_NEXT_DROP; /* Passthrough to drop for now */

            bi0 = to_next[0] = from[0];
            from += 1;
            to_next += 1;
            n_left_from -= 1;
            n_left_to_next -= 1;

            b0 = vlib_get_buffer (vm, bi0);

            (void) b0;

            /* 
             * FFI call will be placed here in Part B.
             * For now, we just pass the packet to the next node.
             */

            vlib_validate_buffer_enqueue_x1 (vm, node, next_index,
                                             to_next, n_left_to_next,
                                             bi0, next0);
        }

        vlib_put_next_frame (vm, node, next_index, n_left_to_next);
    }

    return frame->n_vectors;
}

/* Register the node */
VLIB_REGISTER_NODE (rust_classify_node) = {
    .function = rust_classify_node_fn,
    .name = "rust-classify-node",
    .vector_size = sizeof (u32),
    .format_trace = 0, /* Will be added in Part B */
    .type = VLIB_NODE_TYPE_INTERNAL,
    .n_errors = 0,
    .error_strings = 0,
    .n_next_nodes = RUST_CLASSIFY_N_NEXT,
    .next_nodes = {
        [RUST_CLASSIFY_NEXT_DROP] = "error-drop",
    },
};

/* Register the plugin */
VLIB_PLUGIN_REGISTER () = {
    .version = "1.0",
    .description = "Rust Packet Classification Plugin",
};
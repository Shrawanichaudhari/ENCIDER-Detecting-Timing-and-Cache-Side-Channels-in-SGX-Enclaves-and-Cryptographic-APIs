#include <klee/klee.h>
#define DEPTH 20
int main() {
    unsigned char bits[DEPTH];
    klee_make_symbolic(bits, sizeof(bits), "bits");
    int acc = 0;
    for (int i = 0; i < DEPTH; i++) {
        /* ENCIDER-style secret-dependent branch: the two sides do a
           different amount of work (a stand-in for a timing/cache
           side channel's differing resource usage). */
        if (bits[i] & 1) {
            for (int k = 0; k < 3; k++) acc += (i + 1);
        } else {
            acc += 1;
        }
    }
    return acc & 0xff;
}

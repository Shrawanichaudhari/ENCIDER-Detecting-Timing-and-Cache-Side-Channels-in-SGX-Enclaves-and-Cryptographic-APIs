"""Eq. (2) of the paper (data-cache check from ENCIDER [1], Sec. 5.2.3.2) as a Z3 query.
Leak iff exists H, H' with (A[H] & M) != (A[H'] & M)."""
from z3 import BitVec, Solver, sat, ZeroExt

def data_cache_leak(addr_fn, secret_bits=8, addr_bits=64, line=64):
    H, H2 = BitVec('H', secret_bits), BitVec('H_prime', secret_bits)
    M = ~(line - 1) & ((1 << addr_bits) - 1)          # keep line index, drop offset
    s = Solver()
    s.add((addr_fn(H, addr_bits) & M) != (addr_fn(H2, addr_bits) & M))
    if s.check() == sat:
        m = s.model(); return True, (m[H].as_long(), m[H2].as_long())
    return False, None

BASE = 0x10000                                         # table base, 64-byte aligned
ttable  = lambda h, w: BASE + ZeroExt(w - h.size(), h) * 4        # 256 x 4-byte entries: T[h]
small   = lambda h, w: BASE + ZeroExt(w - h.size(), h & 0xF)      # 16 x 1-byte entries
const   = lambda h, w: BASE + 0 * ZeroExt(w - h.size(), h)        # secret-independent address

for name, fn in [('AES-style T-table T[h]', ttable), ('16-byte table t[h&15]', small), ('constant address', const)]:
    print(f'{name:26s} leak={data_cache_leak(fn)}')

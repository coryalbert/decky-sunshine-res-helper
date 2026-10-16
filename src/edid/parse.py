"""
Minimal EDID reader: does a sink's EDID advertise an exact width x height @ refresh?
"""

from __future__ import annotations

from src.edid.vic import VIC_RESOLUTIONS


def _dtd_mode(d: bytes | bytearray) -> tuple[int, int, int] | None:
    """Decode an 18-byte detailed timing descriptor into (width, height, refresh_hz)."""
    clock = int.from_bytes(d[0:2], "little") * 10_000
    if clock == 0:
        return None  # display descriptor, not a timing
    h_active = d[2] | ((d[4] & 0xF0) << 4)
    h_blank = d[3] | ((d[4] & 0x0F) << 8)
    v_active = d[5] | ((d[7] & 0xF0) << 4)
    v_blank = d[6] | ((d[7] & 0x0F) << 8)
    total = (h_active + h_blank) * (v_active + v_blank)
    if total == 0:
        return None
    return h_active, v_active, round(clock / total)


def edid_supported_modes(edid: bytes) -> set[tuple[int, int, int]]:
    """All (width, height, refresh) the EDID lists as DTDs or CTA-861 VICs.

    DisplayID and extended CTA data blocks are not read.
    """
    modes: set[tuple[int, int, int]] = set()
    if len(edid) < 128:
        return modes

    for off in (54, 72, 90, 108):
        m = _dtd_mode(edid[off:off + 18])
        if m:
            modes.add(m)

    for blk in range(1, len(edid) // 128):
        e = edid[blk * 128:(blk + 1) * 128]
        if e[0] != 0x02 or e[2] < 4:
            continue
        i = 4
        while i < e[2]:
            tag, n = e[i] >> 5, e[i] & 0x1F
            if tag == 2:  # Video Data Block
                for b in e[i + 1:i + 1 + n]:
                    vic = b & 0x7F if 129 <= b <= 192 else b  # 129-192: native flag set
                    if vic in VIC_RESOLUTIONS:
                        w, h, r, _ = VIC_RESOLUTIONS[vic]
                        modes.add((w, h, r))
            i += 1 + n
        i = e[2]
        while i + 18 <= 127:  # DTDs after the data blocks
            m = _dtd_mode(e[i:i + 18])
            if m:
                modes.add(m)
            i += 18
    return modes


def edid_supports_mode(edid: bytes, width: int, height: int, refresh: int) -> bool:
    return (width, height, refresh) in edid_supported_modes(edid)

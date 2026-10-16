import unittest

from src.edid import check_if_calculation_breaks
from src.edid.parse import edid_supported_modes, edid_supports_mode


def _edid_with_vdb(vics: bytes) -> bytes:
    """128-byte base block (no timings) + CTA-861 extension holding one Video Data Block."""
    edid = bytearray(256)
    edid[0:8] = [0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00]
    edid[126] = 1
    ext = 128
    edid[ext], edid[ext + 1] = 0x02, 0x03
    edid[ext + 4] = (2 << 5) | len(vics)
    edid[ext + 5:ext + 5 + len(vics)] = vics
    edid[ext + 2] = 5 + len(vics)  # no DTDs after the data blocks
    return bytes(edid)


def _dtd_1080p60() -> bytes:
    d = bytearray(18)
    d[0:2] = (14850).to_bytes(2, "little")  # 148.5 MHz
    d[2], d[3], d[4] = 1920 & 0xFF, 280 & 0xFF, ((1920 >> 8) << 4) | (280 >> 8)
    d[5], d[6], d[7] = 1080 & 0xFF, 45, ((1080 >> 8) << 4) | (45 >> 8)
    return bytes(d)


class EdidParseTest(unittest.TestCase):
    # Video Data Block of an LG C5: 4K60, 4K50, 4K120 (VIC 118), 4K100 (VIC 117), ...
    LG_C5_VICS = bytes.fromhex("616076756665dbda101f04130514030212202122155d5e5f6263643f40")

    def test_vic_modes(self):
        edid = _edid_with_vdb(self.LG_C5_VICS)
        self.assertTrue(edid_supports_mode(edid, 3840, 2160, 120))
        self.assertTrue(edid_supports_mode(edid, 3840, 2160, 100))
        self.assertTrue(edid_supports_mode(edid, 3840, 2160, 60))
        self.assertFalse(edid_supports_mode(edid, 3840, 2160, 90))
        self.assertFalse(edid_supports_mode(edid, 2560, 1440, 120))

    def test_native_flag_is_ignored(self):
        # VIC 16 (1080p60) with the "native" bit set is byte 0x90
        edid = _edid_with_vdb(bytes([0x90]))
        self.assertTrue(edid_supports_mode(edid, 1920, 1080, 60))

    def test_base_block_dtd(self):
        edid = bytearray(256)
        edid[54:72] = _dtd_1080p60()
        self.assertIn((1920, 1080, 60), edid_supported_modes(bytes(edid)))

    def test_short_or_empty_edid(self):
        self.assertEqual(edid_supported_modes(b""), set())
        self.assertFalse(edid_supports_mode(b"\x00" * 64, 3840, 2160, 120))

    def test_over_limit_modes(self):
        # Only these need the passthrough path; they don't fit a base-block DTD.
        self.assertTrue(check_if_calculation_breaks(3840, 2160, 120))
        self.assertTrue(check_if_calculation_breaks(3840, 2160, 100))
        self.assertFalse(check_if_calculation_breaks(3840, 2160, 60))
        self.assertFalse(check_if_calculation_breaks(2560, 1440, 120))


if __name__ == "__main__":
    unittest.main()

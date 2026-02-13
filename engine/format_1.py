import re
import pandas as pd


def parse(text: str) -> pd.DataFrame:
    # =============================
    # CLEAN TEXT
    # =============================
    text = re.sub(r"[\u200e\u200f\u202a\u202b\u202c\u202d\u202e]", "", text)

    # =============================
    # SPLIT NIK
    # =============================
    blocks = re.split(
    r"""
    (?: 
        # WA HP
        \[\d{1,2}\.\d{2},\s*\d{1,2}/\d{1,2}/\d{4}\]\s*.*?:\s*
        |
        # WA Desktop
        \d{2}/\d{2}/\d{2}\s+\d{2}\.\d{2}\s+-\s+.*?:\s*
    )
    """,
    text,
    flags=re.VERBOSE
    )

    data = []

    BULAN_MAP = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN",
                 "JUL", "AUG", "SEP", "OKT", "NOV", "DES"]

    BAD_WORDS = {"LANJUT_JMO", "NO_MODAL", "TUNGGAL", "IURAN TERAKHIR"}

    # =============================
    # HELPER
    # =============================
    def is_bulan(line: str) -> bool:
        l = line.upper()
        return any(b in l for b in BULAN_MAP) or bool(
            re.fullmatch(
                r"(JAN|FEB|MAR|APR|MEI|JUN|JUL|AUG|AGUS|AGUST|AGU|SEP|OKT|NOV|DES)\s+\d{4}",
                l
            )
        )

    def guess_gender(name: str) -> str:
        name = name.lower()
        female = [
            "sri", "wati", "ani", "eni", "wulandari",
            "sinaga", "sari", "asri", "junitasari", "demmanaba"
        ]
        return "Perempuan" if any(f in name for f in female) else "Laki-laki"

    def hitung_fee(total: int) -> int:
        if total < 1_000_000:
            fee = 32000
        elif total <= 1_599_999:
            fee = total * 0.045
        elif total <= 2_099_999:
            fee = total * 0.04
        elif total <= 2_999_999:
            fee = total * 0.035
        else:
            fee = total * 0.03
        return int(round(fee / 1000) * 1000)

    # =============================
    # PROSES BLOK
    # =============================
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if len(lines) < 5:
            continue

        # =============================
        # VALIDASI NIK
        # =============================
        nik = lines[0] if re.fullmatch(r"\d{16}", lines[0]) else ""
        if not nik:
            continue

        nama = lines[1]
        ttl = lines[3] if re.fullmatch(r"\d{2}-\d{2}-\d{4}", lines[3]) else ""

        email = ""
        perusahaan = ""
        periode = ""
        sensor = ""
        saldo_list = []

        idx = 4

        # =============================
        # EMAIL
        # =============================
        if idx < len(lines) and "@" in lines[idx]:
            email = lines[idx]
            idx += 1

        # =============================
        # BODY PARSING
        # =============================
        while idx < len(lines):
            line = lines[idx]
            upper = line.upper()

            if "LOKASI" in upper:
                break

            if upper in BAD_WORDS:
                idx += 1
                continue

            if is_bulan(line):
                periode = line

            elif "*" in line:
                sensor = re.sub(r"[^0-9*]", "", line)

            elif re.fullmatch(r"[0-9.,* ]+", line):
                clean = re.sub(r"[^\d]", "", line)
                if clean:
                    saldo_list.append(clean)

            elif re.search(r"[A-Za-z]", line) and not perusahaan:
                perusahaan = line

            idx += 1

        # =============================
        # LOKASI
        # =============================
        kota = kec = kel = ""
        for i, l in enumerate(lines):
            if "LOKASI" in l.upper() and i + 3 < len(lines):
                kota = lines[i + 1].replace("*", "")
                kec = lines[i + 2].replace("*", "")
                kel = lines[i + 3].replace("*", "")
                break

        total_saldo = sum(map(int, saldo_list)) if saldo_list else 0

        data.append({
            "NIK": nik,
            "Nama": nama,
            "Tanggal Lahir": ttl,
            "Jenis Kelamin": guess_gender(nama),
            "Kelurahan": kel,
            "Kecamatan": kec,
            "Kota/Kabupaten": kota,
            "Perusahaan": perusahaan,
            "Periode": periode,
            "Sensor": sensor or "Tunggal",
            "Saldo": ",".join(saldo_list),
            "Total Saldo": total_saldo,
            "Fee": hitung_fee(total_saldo),
            "Details": "",
            "Akun": email
        })

    return pd.DataFrame(data).drop_duplicates(subset=["NIK"])
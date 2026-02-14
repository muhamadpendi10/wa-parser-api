import re
import pandas as pd

BAD_WORDS = ["IURAN TERAKHIR", "LANJUT_JMO", "NO_MODAL", "TUNGGAL"]
SENSOR_REGEX = re.compile(r"^(\d+\*+\s*)+$")
SALDO_LABEL_REGEX = re.compile(r"^\d+\s*SALDO$", re.IGNORECASE)


# =============================
# HELPER FUNCTIONS
# =============================
def guess_gender(name):
    name = name.lower()
    female = ["sri","wati","ani","eni","wulandari","sari","asri","junitasari"]
    return "Perempuan" if any(w in name for w in female) else "Laki-laki"


def hitung_fee(total_saldo):
    if total_saldo < 1_000_000:
        fee = 32000
    elif total_saldo <= 1_599_999:
        fee = total_saldo * 0.045
    elif total_saldo <= 2_099_999:
        fee = total_saldo * 0.04
    elif total_saldo <= 2_999_999:
        fee = total_saldo * 0.035
    else:
        fee = total_saldo * 0.03

    return int(round(fee / 1000) * 1000)


def clean_kota(value):
    if not value:
        return ""

    value = value.upper().strip()
    value = re.sub(r"^(KOTA\s+ADM\.?\s*)", "", value)
    value = re.sub(r"^(KOTA\s+ADMINISTRASI\s*)", "", value)
    value = re.sub(r"^(KOTA\s*)", "", value)
    value = re.sub(r"^(KABUPATEN\s*)", "", value)

    return value.strip()


# =============================
# MAIN PARSER FUNCTION
# =============================
def parse(text: str) -> pd.DataFrame:

    # =============================
    # CLEAN TEXT
    # =============================
    text = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", text)
    text = re.sub(r"[\u2600-\u27BF]", "", text)

    # =============================
    # SPLIT BLOCK WHATSAPP FORMAT 2
    # =============================
    blocks = re.split(
        r"\d{2}/\d{2}/\d{2}\s+\d{2}\.\d{2}\s+-\s+\+\d.*?:\s*",
        text
    )

    data = []

    for block in blocks:

        lines = [l.strip() for l in block.split("\n") if l.strip()]
        full_block_text = " ".join(lines)

        if not any("NIK" in l.upper() for l in lines):
            continue

        nama = nik = ttl = email = ""
        perusahaan = periode = ""
        kota = kelurahan = kecamatan = ""
        sensor = ""
        saldo_list = []

        idx = 0

        # =============================
        # IDENTITAS
        # =============================
        while idx < len(lines):
            line = lines[idx]
            upper = line.upper()

            if upper.startswith("NAMA"):
                nama = line.split(":",1)[1].strip()

            elif re.match(r"^NIK\s*:", line, re.IGNORECASE):
                nik = re.sub(r"\D", "", line.split(":",1)[1])

            elif upper.startswith("TTL"):
                match = re.search(r"\d{2}-\d{2}-\d{4}", line)
                ttl = match.group(0) if match else ""

            elif "@" in line:
                email = line
                idx += 1
                break

            idx += 1

        # =============================
        # SKIP SALDO LABEL
        # =============================
        while idx < len(lines) and SALDO_LABEL_REGEX.fullmatch(lines[idx]):
            idx += 1

        # =============================
        # SALDO
        # =============================
        while idx < len(lines) and re.fullmatch(r"[0-9.,]+", lines[idx]):
            clean = lines[idx].replace(".", "").replace(",", "")
            saldo_list.append(clean)
            idx += 1

        # =============================
        # SENSOR
        # =============================
        while idx < len(lines):
            line = lines[idx]

            if SENSOR_REGEX.fullmatch(line):
                sensor = line
                idx += 1
                continue

            if "SENSOR" in line.upper():
                idx += 1
                continue

            break

        # =============================
        # PERUSAHAAN
        # =============================
        if idx < len(lines) and lines[idx].upper() not in BAD_WORDS:
            perusahaan = lines[idx]
            idx += 1

        while idx < len(lines) and lines[idx].upper() in BAD_WORDS:
            idx += 1

        # =============================
        # PERIODE
        # =============================
        if idx < len(lines):
            periode = lines[idx]
            idx += 1

        # ==========================================================
        # PRIORITAS 1 — LABEL DETECTION
        # ==========================================================
        kel_match = re.search(
            r"KELURAHAN\s*:\s*(.*?)(?=\s+KECAMATAN|\s+KOTA|\s+KABUPATEN|$)",
            full_block_text,
            re.IGNORECASE
        )

        kec_match = re.search(
            r"KECAMATAN\s*:\s*(.*?)(?=\s+KOTA|\s+KABUPATEN|$)",
            full_block_text,
            re.IGNORECASE
        )

        kota_match = re.search(
            r"(KOTA|KABUPATEN)\s*:\s*(.*?)(?=\s+[A-Z]+\s*:|$)",
            full_block_text,
            re.IGNORECASE
        )

        label_found = False

        if kel_match:
            kelurahan = kel_match.group(1).strip()
            label_found = True

        if kec_match:
            kecamatan = kec_match.group(1).strip()
            label_found = True

        if kota_match:
            kota = kota_match.group(2).strip()
            label_found = True

        # ==========================================================
        # PRIORITAS 2 — FALLBACK
        # ==========================================================
        if not label_found:
            while idx < len(lines):
                line = lines[idx].strip()
                if not kota:
                    kota = line
                elif not kelurahan:
                    kelurahan = line
                elif not kecamatan:
                    kecamatan = line
                idx += 1

        # =============================
        # HITUNG SALDO
        # =============================
        saldo = ",".join(saldo_list)
        total_saldo = sum(int(s) for s in saldo_list) if saldo_list else 0
        fee = hitung_fee(total_saldo)

        data.append({
            "NIK": nik,
            "Nama": nama,
            "Tanggal Lahir": ttl,
            "Jenis Kelamin": guess_gender(nama),
            "Kelurahan": kelurahan,
            "Kecamatan": kecamatan,
            "Kota/Kabupaten": clean_kota(kota),
            "Perusahaan": perusahaan,
            "Periode": periode,
            "Sensor": sensor if sensor else "Tunggal",
            "Saldo": saldo,
            "Total Saldo": total_saldo,
            "Fee": fee,
            "Details": "",
            "Akun": email
        })

    df = pd.DataFrame(data)
    return df.drop_duplicates(subset=["NIK"])

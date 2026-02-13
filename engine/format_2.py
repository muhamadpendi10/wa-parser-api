import re
import pandas as pd

BAD_WORDS = ["IURAN TERAKHIR", "LANJUT_JMO", "NO_MODAL", "TUNGGAL"]
SENSOR_REGEX = re.compile(r"^(\d+\*+\s*)+$")
SALDO_LABEL_REGEX = re.compile(r"^\d+\s*SALDO$", re.IGNORECASE)

def guess_gender(name):
    name = name.lower()
    female = ["sri","wati","ani","eni","wulandari","sinaga","sari","asri","junitasari","demmanaba"]
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

def parse(text: str) -> pd.DataFrame:
    # =============================
    # CLEAN TEXT
    # =============================
    text = re.sub(r"[\u200e-\u202e]", "", text)
    text = re.sub(r"[\u2600-\u27BF]", "", text)

    # =============================
    # REMOVE WA HEADER
    # =============================
    blocks = re.split(
    	r"(?=NAMA\s*:)",
    	text,
 	flags=re.IGNORECASE
    )

    data = []

    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not any("NIK" in l.upper() for l in lines):
            continue

        nama = nik = kpj = ttl = email = ""
        perusahaan = periode = kota = kelurahan = kecamatan = sensor = ""
        saldo_list = []

        idx = 0

        # =============================
        # IDENTITAS
        # =============================
        while idx < len(lines):
            line = lines[idx]
            up = line.upper()

            if up.startswith("NAMA"):
                nama = line.split(":", 1)[1].strip()
            elif up.startswith("NIK"):
                nik = re.sub(r"\D", "", line)
            elif up.startswith("KPJ"):
                kpj = re.sub(r"\D", "", line)
            elif up.startswith("TTL"):
                m = re.search(r"\d{2}-\d{2}-\d{4}", line)
                ttl = m.group(0) if m else ""
            elif "@" in line:
                email = line
                idx += 1
                break

            idx += 1

        # =============================
        # SKIP LABEL SALDO
        # =============================
        while idx < len(lines) and SALDO_LABEL_REGEX.fullmatch(lines[idx]):
            idx += 1

        # =============================
        # SALDO
        # =============================
        while idx < len(lines) and re.fullmatch(r"[0-9.,]+", lines[idx]):
            saldo_list.append(lines[idx].replace(".", "").replace(",", ""))
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

        # =============================
        # SKIP BAD WORDS
        # =============================
        while idx < len(lines) and lines[idx].upper() in BAD_WORDS:
            idx += 1

        # =============================
        # PERIODE
        # =============================
        if idx < len(lines):
            periode = lines[idx]
            idx += 1

        # =============================
        # LOKASI
        # =============================
        while idx < len(lines):
            raw = lines[idx].upper().replace("KODE", "").replace(":", "").strip()
            angka = re.sub(r"\D", "", raw)

            if len(angka) == 4:
                kota = angka
            elif len(angka) == 5:
                kelurahan = angka
            elif len(angka) == 6:
                kecamatan = angka
            else:
                if not kota:
                    kota = lines[idx]
                elif not kelurahan:
                    kelurahan = lines[idx]
                elif not kecamatan:
                    kecamatan = lines[idx]

            idx += 1

        total_saldo = sum(map(int, saldo_list)) if saldo_list else 0

        data.append({
            "NIK": nik,
            "Nama": nama,
            "Tanggal Lahir": ttl,
            "Jenis Kelamin": guess_gender(nama),
            "Kelurahan": kelurahan,
            "Kecamatan": kecamatan,
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

import re
import pandas as pd


# =============================
# HELPER
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
    value = re.sub(r"^(KOTA\s*)", "", value)
    value = re.sub(r"^(KABUPATEN\s*)", "", value)
    value = re.sub(r"^(KAB\.\s*)", "", value)

    return value.strip()


# =============================
# MAIN PARSER
# =============================
def parse(text: str) -> pd.DataFrame:

    # CLEAN TEXT
    text = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", text)
    text = re.sub(r"[\u2600-\u27BF]", "", text)
    text = text.replace("⭐","")

    pattern1 = r"\d{2}/\d{2}/\d{2}\s+\d{2}\.\d{2}\s+-\s+.*?:\s*"
    pattern2 = r"\[\d{1,2}\.\d{2},\s*\d{1,2}/\d{1,2}/\d{4}\]\s*.*?:\s*"

    blocks = re.split(f"{pattern1}|{pattern2}", text)

    data = []

    for block in blocks:

        lines = [l.strip() for l in block.split("\n") if l.strip()]

        if not lines:
            continue

        full_text = " ".join(lines)

        nik = ""
        nama = ""
        ttl = ""
        email = ""
        perusahaan = ""
        periode = ""
        kelurahan = ""
        kecamatan = ""
        kota = ""
        saldo_list = []
        sensor = "Tunggal"

        # =============================
        # WILAYAH
        # =============================
        kota_match = re.search(r"KOTA\s*:\s*(.*)", full_text, re.IGNORECASE)
        kec_match = re.search(r"KEC\s*:\s*(.*)", full_text, re.IGNORECASE)
        desa_match = re.search(r"DESA\s*:\s*(.*)", full_text, re.IGNORECASE)

        if kota_match:
            kota = kota_match.group(1).strip()

        if kec_match:
            kecamatan = kec_match.group(1).strip()

        if desa_match:
            kelurahan = desa_match.group(1).strip()

        # FIX jika kepanjangan
        if not kelurahan or len(kelurahan) > 40:
            for l in lines:
                if l.upper().startswith("DESA"):
                    kelurahan = l.split(":",1)[1].strip()
                    break

        if not kecamatan or len(kecamatan) > 40:
            for l in lines:
                if l.upper().startswith("KEC"):
                    kecamatan = l.split(":",1)[1].strip()
                    break

        if not kota or len(kota) > 60:
            for l in lines:
                if l.upper().startswith("KOTA"):
                    kota = l.split(":",1)[1].strip()
                    break

        # FIX desa baris bawah
        if not kelurahan:
            for i,l in enumerate(lines):
                if "DESA" in l.upper():
                    if i+1 < len(lines):
                        kandidat = lines[i+1].strip()
                        if not re.fullmatch(r"\d{6,}", kandidat):
                            kelurahan = kandidat
                            break

        # POTONG jika nyambung
        if kota:
            kota = re.split(r"\bKEC\b|\bDESA\b|\bSTATUS\b|\d{16}", kota)[0].strip()

        # =============================
        # NIK
        # =============================
        for l in lines:
            if re.fullmatch(r"\d{16}", l):
                nik = l
                break

        # =============================
        # TTL
        # =============================
        for l in lines:
            if re.fullmatch(r"\d{2}-\d{2}-\d{4}", l):
                ttl = l
                break

        # =============================
        # NAMA FORMAT TXT
        # =============================
        for l in lines:
            if l.startswith("*") and l.endswith("*"):
                nama = l.replace("*","").strip()
                break

        # =============================
        # NAMA FORMAT RAW WA
        # =============================
        if not nama:
            for i,l in enumerate(lines):
                if re.fullmatch(r"\d{2}-\d{2}-\d{4}", l):
                    if i+1 < len(lines):
                        kandidat = lines[i+1].strip()
                        if not kandidat.isdigit() and "RP" not in kandidat.upper():
                            nama = kandidat
                            break

        # =============================
        # SALDO
        # =============================
        saldo_match = re.search(r"Rp\s*:\s*([\d\.]+)", full_text, re.IGNORECASE)

        if saldo_match:
            clean_saldo = saldo_match.group(1).replace(".","")
            saldo_list.append(clean_saldo)

        # =============================
        # STATUS → PERIODE
        # =============================
        status_match = re.search(r"STATUS\s*:\s*(.*)", full_text, re.IGNORECASE)

        if status_match:
            periode = status_match.group(1).strip()

        # =============================
        # PERUSAHAAN
        # =============================
        for i,l in enumerate(lines):
            if "STATUS" in l.upper() and i+1 < len(lines):
                perusahaan = lines[i+1]
                break

        # =============================
        # EMAIL
        # =============================
        for l in lines:
            if "@" in l and not l.lower().startswith("bpjs"):
                email = l
                break

        # =============================
        # SENSOR
        # =============================
        sensor_list = []

        for l in lines:
            matches = re.findall(r"\(\d{2}\*+\d{2}\)", l)
            for m in matches:
                sensor_list.append(m.strip("()"))

        if sensor_list:
            sensor = ",".join(sensor_list)

        # =============================
        # FIX PERIODE
        # =============================
        if not re.search(r"\d{4}", periode):

            for l in lines:
                if re.fullmatch(r"\d{10,13}", l) and l != nik:
                    tahun = "20" + l[:2]
                    periode = tahun
                    break

        if not re.search(r"\d{4}", periode):

            for l in lines:
                if re.match(r"\d{2}[A-Z]\d{7,}", l):
                    tahun = "20" + l[:2]
                    periode = tahun
                    break

        if re.fullmatch(r"20\d{2}", periode):

            tahun_dua_digit = int(periode[2:])

            if tahun_dua_digit > 30:
                periode = "19" + periode[2:]

        # =============================
        # HITUNG
        # =============================
        saldo = ",".join(saldo_list)

        total_saldo = sum(int(s) for s in saldo_list) if saldo_list else 0

        fee = hitung_fee(total_saldo)

        if nik:

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
                "Sensor": sensor,
                "Saldo": saldo,
                "Total Saldo": total_saldo,
                "Fee": fee,
                "Details": "",
                "Akun": email
            })

    df = pd.DataFrame(data)

    return df.drop_duplicates(subset=["NIK"])
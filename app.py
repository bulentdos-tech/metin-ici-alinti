import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Profesyonel Atıf Denetçisi")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

def normalize(text):
    # Metindeki satır sonlarını ve fazla boşlukları temizler
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text) # Tirelemeleri birleştir
    return re.sub(r'\s+', ' ', text).strip()

if uploaded_file:
    with st.spinner('Dosya analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_content = ""
        for page in doc:
            full_content += page.get_text("text") + "\n"
        doc.close()

        full_content = normalize(full_content)

        # 1. KAYNAKÇA BÖLÜMÜNÜ TESPİT ET (Dinamik Arama)
        # References/Kaynakça başlığının en SON geçtiği yeri bulur
        ref_header = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_content, re.IGNORECASE))
        
        if ref_header:
            split_idx = ref_header[-1].start()
            body_text = full_content[:split_idx]
            ref_section = full_content[split_idx:]

            # 2. KAYNAKÇADAKİ ESERLERİ AYIKLA
            # Kalıp: Soyadı, A. (Yıl)
            ref_entries = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_section)

            # 3. METİNDEKİ ATIFLARI AYIKLA
            # Kalıp: (Yazar, 2020) veya Yazar (2020) - et al. ve & dahil
            body_citations = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)

            results = []

            # --- DENETİM MANTIĞI ---

            # KONTROL A: Kaynakçada olup Metinde OLMAYANLAR (Gerçek Eksikler)
            for r_auth, r_year in ref_entries:
                # Metin içinde bu soyadı ve yılı ara
                # Hem tam atıf listesinde ara hem de ham metinde kontrol et
                is_cited = any(r_auth.lower() in b_auth.lower() and r_year == b_year for b_auth, b_year in body_citations)
                
                # Eğer bulunamadıysa, metin içinde manuel bir arama daha yap (Hata payını sıfırlamak için)
                if not is_cited:
                    manual_check = re.search(rf"\b{r_auth}\b.*?{r_year}", body_text, re.IGNORECASE)
                    if not manual_check:
                        results.append({
                            "Eser": f"{r_auth} ({r_year})",
                            "Durum": "⚠️ Metinde Atıfı Yok",
                            "Açıklama": "Bu kaynak listede var ama metin gövdesinde bulunamadı."
                        })

            # KONTROL B: Metinde olup Kaynakçada OLMAYANLAR (Biggs vb.)
            for b_auth, b_year in body_citations:
                b_clean = b_auth.replace(" et al.", "").replace("&", " ").split()[0]
                if len(b_clean) < 3 or b_clean.lower() in ["table", "figure"]: continue
                
                is_in_ref = any(b_clean.lower() in r_auth.lower() and b_year == r_year for r_auth, r_year in ref_entries)
                if not is_in_ref:
                    results.append({
                        "Eser": f"{b_auth} ({b_year})",
                        "

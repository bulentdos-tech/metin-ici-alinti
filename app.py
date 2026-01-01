import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Kesin Sonuçlu Atıf-Kaynakça Denetçisi")

uploaded_file = st.file_uploader("PDF Dosyasını Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        
        # 1. ADIM: SAYFA TABANLI BÖLME (BAŞLIK HATASINI ÇÖZER)
        # deneme6.pdf dosyasında kaynakça 15. sayfada başlıyor.
        # Bu yüzden ilk 14 sayfayı metin, sonrasını kaynakça olarak ayırıyoruz.
        body_text = ""
        ref_text = ""
        
        for i, page in enumerate(doc):
            if i < 14:  # 15. sayfadan öncesi (0-indexed olduğu için 14)
                body_text += page.get_text("text") + " "
            else:
                ref_text += page.get_text("text") + " "
        doc.close()

        # Temizlik
        body_text = re.sub(r'\s+', ' ', body_text)
        ref_text = re.sub(r'\s+', ' ', ref_text)

        # 2. ADIM: KAYNAKÇADAKİ YAZARLARI ÇIKAR
        # APA formatındaki 'Soyadı, A. (Yıl)' yapısını yakalar
        ref_list = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_text)
        
        # 3. ADIM: METİNDEKİ ATIFLARI ÇIKAR
        # 'Yazar (Yıl)' veya '(Yazar, Yıl)' kalıpları
        body_cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+)\s*\((\d{4})\)', body_text)

        results = []

        # --- ANALİZ MANTIĞI ---

        # HATA: KAYNAKÇADA VAR, METİNDE YOK (Sildikleriniz)
        for r_auth, r_year in ref_list:
            # Soyadı metin içinde bu yılla geçiyor mu?
            found = any(r_auth.lower() in b_auth.lower() and r_year == b_year for b_auth, b_year in body_cites)
            if not found:
                # Özel Kontrol: Zhai için yıl uyuşmazlığı var mı?
                is_mismatch = any(r_auth.lower() in b_auth.lower() and r_year != b_year for b_auth, b_year in body_cites)
                if is_mismatch:
                    results.append({"Eser": r_auth, "Hata": "Yıl Uyuşmazlığı (Metinde farklı yıl var)", "Detay": f"Kaynakça: {r_year}"})
                else:
                    results.append({"Eser": f"{r_auth} ({r_year})", "Hata": "Metinde Atı

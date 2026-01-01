import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Akıllı Atıf-Kaynakça Çapraz Denetçi")

uploaded_file = st.file_uploader("PDF Dosyasını Yükleyin", type="pdf")

def temizle(metin):
    # Satır sonu tirelemelerini ve gereksiz boşlukları temizler
    metin = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', metin)
    return re.sub(r'\s+', ' ', metin).strip()

if uploaded_file:
    with st.spinner('Dosya taranıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        
        full_text = temizle(full_text)

    # 1. BÖLÜM: KAYNAKÇA AYIRMA
    ref_baslik = re.search(r'\n\s*(References|Kaynakça|KAYNAKÇA)\s*\n', full_text, re.IGNORECASE)
    if ref_baslik:
        split_idx = ref_baslik.start()
        body_text = full_text[:split_idx]
        ref_text = full_text[split_idx:]

        # 2. BÖLÜM: KAYNAKÇADAKİ ESERLERİ BUL (Hyland, Perkins, Swales vb.)
        # APA formatında yazar soyadı ve yılı çeker
        ref_entries = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_text)
        
        # 3. BÖLÜM: METİN İÇİNDEKİ ATIFLARI BUL (Zhai, Biggs & Tang vb.)
        # (Yazar, 2020) veya Yazar (2020) kalıplarını arar
        body_citations = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)

        # --- ANALİZ ---
        sonuclar = []

        # HATA 1: Kaynakçada var ama METİNDE YOK (Sildiğiniz atıflar)
        for r_auth, r_year in ref_entries:
            # Metinde yazar soyadı ve yılı yan yana geçiyor mu?
            found = any(r_auth.lower() in b_auth.lower() and r_year == b_year for b_auth, b_year in body_citations)
            if not found:
                sonuclar.append({"Yazar/Eser": f"{r_auth} ({r_year})", "Hata Türü": "Metinde Atıfı Yok (SİLİNMİŞ)", "Konum": "Kaynakça Listesi"})

        # HATA 2: Metinde atıf var ama KAYNAKÇADA YOK (Unutulanlar)
        for b_auth, b_year in body_citations:
            # Temizleme: "Biggs & Tang" içinden sadece soyadları kontrol et
            b_clean = b_auth.replace(" et al.", "").replace("&", " ").split()[0]
            found_in_ref = any(b_clean.lower() in r_auth.lower() and b_year == r_year for r_auth, r_year in ref_entries)
            
            if not found_in_ref:
                sonuclar.append({"Yazar/Eser": f"{b_auth} ({b_year})", "Hata Türü": "Kaynakçada Kaydı Yok (EKSİK)", "Konum": "Metin İçindeki Atıf"})

        # HATA 3: YIL UYUŞMAZLIĞI (Zhai 2022 vs 2023)
        for r_auth, r_year in ref_entries:
            for b_auth, b_year in body_citations:
                if r_auth.lower() in b_auth.lower() and r_year != b_year:
                    sonuclar.append({"Yazar/Eser": r_auth, "Hata Türü": f"Yıl Uyuşmazlığı (Metin: {b_year}, Kaynakça: {r_year})", "Konum": "Genel"})

        # --- TABLOYU GÖSTER ---
        df_sonuc = pd.DataFrame(sonuclar).drop_duplicates()
        if not df_sonuc.empty:
            st.error("⚠️ Tutarsızlıklar Tespit Edildi:")
            st.table(df_sonuc)
        else:
            st.success("✅ Tebrikler! Metin ve kaynakça %100 uyumlu.")
    else:
        st.error("Kaynakça başlığı bulunamadı.")

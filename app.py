import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Kesin Sonuçlu Atıf Denetçisi")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Derin analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        
        # Gereksiz boşlukları ve gizli karakterleri temizle
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. ADIM: KAYNAKÇAYI DOĞRU YERDEN KES (Garantili Yöntem)
    # References kelimesinin EN SON geçtiği yeri bul
    all_refs = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE))
    
    if all_refs:
        split_idx = all_refs[-1].start() # En sondaki başlığı baz al
        body_text = full_text[:split_idx]
        ref_text = full_text[split_idx:]

        # 2. ADIM: KAYNAKÇADAKİ ESERLERİ LİSTELE
        # Soyadı, A. (Yıl) yapısını yakalar
        refs = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_text)

        # 3. ADIM: METİNDEKİ ATIFLARI LİSTELE
        # Yazar (Yıl) veya (Yazar, Yıl) yapılarını yakalar
        cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+)\s*\((\d{4}[a-z]?)\)', body_text)

        results = []

        # --- KRİTİK KONTROL: KAYNAKÇADA VAR METİNDE YOK ---
        for r_auth, r_year in refs:
            # Metinde bu yazar VE bu yıl yan yana geçiyor mu?
            # Tam kelime eşleşmesi (\b) kullanarak 'Swales' ararken 'Sweller'ı bulmasını engelliyoruz.
            pattern = rf"\b{r_auth}\b.*?{r_year}"
            found = re.search(pattern, body_text, re.IGNORECASE)
            
            if not found:
                results.append({
                    "Eser": f"{r_auth} ({r_year})",
                    "Hata": "⚠️ Metinde Atıfı Yok",
                    "Açıklama": "Bu kaynak sildiğiniz için veya unutulduğu için metinde bulunamadı."
                })

        # --- KRİTİK KONTROL: METİNDE VAR KAYNAKÇADA YOK ---
        for c_auth, c_year in cites:
            c_clean = c_auth.replace(" et al.", "").replace("&", " ").split()[0].strip()
            if c_clean.lower() in ["table", "figure", "appendix"]: continue
            
            in_ref = re.search(rf"\b{c_clean}\b.*?{c_year}", ref_text, re.IGNORECASE)
            if not in_ref:
                results.append({
                    "Eser": f"{c_auth} ({c_year})",
                    "Hata": "❌ Kaynakçada Yok",
                    "Açıklama": "Metinde atıf var ama kaynakça listesinde eksik."
                })

        # SONUÇLARI GÖSTER
        st.divider()
        df = pd.DataFrame(results).drop_duplicates()
        if not df.empty:
            st.error(f"🔍 Toplam {len(df)} tutarsızlık bulundu:")
            st.table(df)
        else:
            st.success("✅ Tebrikler! Metin ve kaynakça %100 uyumlu görünüyor.")
    else:
        st.error("Kaynakça (References) başlığı bulunamadı.")

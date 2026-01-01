import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Profesyonel Atıf & Kaynakça Denetçisi")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

def metin_onarma(text):
    # PDF satır sonu ve boşluk hatalarını temizler
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    return " ".join(text.split())

if uploaded_file:
    with st.spinner('Derin analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        full_text = metin_onarma(full_text)

    # 1. BÖLÜM: KAYNAKÇAYI AYIR
    ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE))
    
    if ref_matches:
        split_point = ref_matches[-1].start()
        body_text = full_text[:split_point]
        ref_section = full_text[split_point:]

        # 2. BÖLÜM: KAYNAKÇADAKİ GERÇEK ESERLERİ BUL
        # Sadece yazar soyadı ile başlayan (References kelimesini hariç tutan) yapıları yakalar
        # Soyadı, A. (Yıl) formatı
        ref_entries = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_section)
        
        # Kara liste: Yazar soyadı olamayacak kelimeler
        kara_liste = ["References", "Kaynakça", "KAYNAKÇA", "Table", "Figure", "Page"]

        # 3. BÖLÜM: METİN İÇİ ATIFLARI YAKALA
        # (Yazar, 2023) veya Yazar (2023) - et al. ve & dahil
        body_cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ&, ]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        
        errors = []

        # --- DENETİM 1: KAYNAKÇADA VAR -> METİNDE YOK (Hyland, Perkins, Swales) ---
        for r_auth, r_year in ref_entries:
            if r_auth in kara_liste: continue
            
            # Metinde yazar ve yılı esnek arama ile bul
            if not re.search(rf"\b{r_auth}\b.*?{r_year}", body_text, re.IGNORECASE):
                errors.append({
                    "Eser": f"{r_auth} ({r_year})",
                    "Hata Türü": "⚠️ Metinde Atıfı Yok",
                    "Açıklama": "Bu kaynak listede var ama metin gövdesinde bulunamadı."
                })

        # --- DENETİM 2: METİNDE VAR -> KAYNAKÇADA YOK (Biggs & Tang, Baidoo-Anu) ---
        for b_auth, b_year in body_cites:
            # Atıftaki ilk soyadı al
            b_clean = b_auth.replace(" et al.", "").replace("&", " ").replace(",", " ").split()[0].strip()
            if b_clean in kara_liste or len(b_clean) < 3: continue
            
            # Kaynakça içinde bu soyadı ve yılı ara
            if not re.search(rf"\b{b_clean}\b.*?{b_year}", ref_section, re.IGNORECASE):
                errors.append({
                    "Eser": f"{b_auth.strip()} ({b_year})",
                    "Hata Türü": "❌ Kaynakçada Yok",
                    "Açıklama": "Metinde bu esere atıf yapılmış ancak kaynakça listesinde eksik."
                })

        # SONUÇLARI GÖSTER
        st.divider()
        df_errors = pd.DataFrame(errors).drop_duplicates()
        
        if not df_errors.empty:
            st.error(f"🔍 Toplam {len(df_errors)} tutarsızlık tespit edildi:")
            st.table(df_errors)
        else:
            st.success("✅ Tebrikler! Metin ve Kaynakça %100 uyumlu görünüyor.")
    else:
        st.error("Kaynakça başlığı bulunamadı.")

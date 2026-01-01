import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Profesyonel Atıf & Kaynakça Denetçisi")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Derin analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        
        # Metni stabilize et (Satır sonlarını ve boşlukları onar)
        full_text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', full_text)
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. BÖLÜM: KAYNAKÇA AYIRIMI
    # En sondaki References kelimesini bul
    ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE))
    
    if ref_matches:
        split_idx = ref_matches[-1].start()
        body_text = full_text[:split_idx]
        ref_section = full_text[split_idx:]

        # 2. BÖLÜM: KAYNAKÇADAKİ ESERLERİ ÇIKAR
        # Sadece Soyadı, A. (Yıl) formatını alır. References kelimesini eler.
        raw_refs = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_section)
        
        # 3. BÖLÜM: METİN İÇİ ATIFLARI ÇIKAR
        # Biggs & Tang (2011) veya (Zhai, 2023) gibi akademik yapıları bulur
        body_cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ&, ]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)

        results = []
        forbidden_words = ["references", "kaynakça", "table", "figure", "abstract"]

        # --- DENETİM A: KAYNAKÇADA VAR -> METİNDE YOK (Hyland, Perkins, Swales...) ---
        for r_auth, r_year in raw_refs:
            if r_auth.lower() in forbidden_words: continue
            
            # Metin gövdesinde soyadı ve yılı ara
            found_in_body = re.search(rf"\b{r_auth}\b.*?{r_year}", body_text, re.IGNORECASE)
            
            if not found_in_body:
                results.append({
                    "Eser": f"{r_auth} ({r_year})",
                    "Hata Türü": "⚠️ Metinde Atıfı Yok",
                    "Açıklama": "Bu kaynak listede duruyor ama metinden sildiğiniz için bulunamadı."
                })

        # --- DENETİM B: METİNDE VAR -> KAYNAKÇADA YOK (Biggs & Tang, Baidoo-Anu...) ---
        for b_auth, b_year in body_cites:
            # Soyadını temizle
            b_clean = b_auth.replace(" et al.", "").replace("&", " ").replace(",", " ").split()[0].strip()
            
            if b_clean.lower() in forbidden_words or len(b_clean) < 3: continue
            
            # Kaynakça bloğunda bu ismi ve yılı ara
            found_in_ref = re.search(rf"\b{b_clean}\b.*?{b_year}", ref_section, re.IGNORECASE)
            
            if not found_in_ref:
                results.append({
                    "Eser": f"{b_auth.strip()} ({b_year})",
                    "Hata Türü": "❌ Kaynakçada Kaydı Yok",
                    "Açıklama": "Metinde atıf yapılmış ancak kaynakça listesine eklenmemiş."
                })

        # SONUÇLARI GÖSTER
        st.divider()
        df = pd.DataFrame(results).drop_duplicates()
        
        if not df.empty:
            st.error(f"🔍 Toplam {len(df)} adet tutarsızlık bulundu:")
            st.table(df)
        else:
            st.success("✅ Tebrikler! Metin ve Kaynakça tam uyumlu görünüyor.")
    else:
        st.error("Dosyada 'References' veya 'Kaynakça' başlığı tespit edilemedi.")

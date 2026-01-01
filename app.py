import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Profesyonel Atıf & Kaynakça Denetçisi")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        
        # Metni temizle ve normalize et
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. BÖLÜM: KAYNAKÇAYI AYIR
    # En sondaki References kelimesini bul
    ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE))
    
    if ref_matches:
        split_idx = ref_matches[-1].start()
        body_text = full_text[:split_idx]
        ref_section = full_text[split_idx:]

        # 2. BÖLÜM: KAYNAKÇADAKİ ESERLERİ ÇIKAR
        # Sadece yazar soyadı formatındakileri al, References'ı kesinlikle alma
        # Bu regex 'Soyadı, A.' yapısını daha sıkı kontrol eder
        raw_refs = re.findall(r'\b([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_section)
        
        # 3. BÖLÜM: METİN İÇİ ATIFLARI ÇIKAR
        # Metindeki (Yazar, 2023) veya Yazar (2023) kalıpları
        body_cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ&, ]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)

        results = []
        # Kesin Yasaklı Kelimeler (Yazar olamazlar)
        blacklist = ["References", "Kaynakça", "KAYNAKÇA", "Table", "Figure", "Abstract", "Appendix"]

        # --- DENETİM A: KAYNAKÇADA VAR -> METİNDE YOK (Hyland, Perkins vb.) ---
        for r_auth, r_year in raw_refs:
            if r_auth in blacklist: continue
            
            # Metinde yazar ve yılı esnek arama ile bul
            if not re.search(rf"\b{r_auth}\b.*?{r_year}", body_text, re.IGNORECASE):
                results.append({
                    "Eser": f"{r_auth} ({r_year})",
                    "Hata Türü": "⚠️ Metinde Atıfı Yok",
                    "Detay": "Kaynakçada duruyor ama metinden sildiğiniz için bulunamadı."
                })

        # --- DENETİM B: METİNDE VAR -> KAYNAKÇADA YOK (Biggs & Tang vb.) ---
        for b_auth, b_year in body_cites:
            # Atıftaki ilk soyadı al
            b_clean = b_auth.replace(" et al.", "").replace("&", " ").replace(",", " ").split()[0].strip()
            
            if b_clean in blacklist or len(b_clean) < 3: continue
            
            # Kaynakça bloğunda bu ismi ve yılı ara
            if not re.search(rf"\b{b_clean}\b.*?{b_year}", ref_section, re.IGNORECASE):
                results.append({
                    "Eser": f"{b_auth.strip()} ({b_year})",
                    "Hata Türü": "❌ Kaynakçada Kaydı Yok",
                    "Detay": "Metinde atıf var ama kaynakça listesinde eksik."
                })

        # SONUÇLARI GÖSTER
        st.divider()
        df = pd.DataFrame(results).drop_duplicates()
        
        if not df.empty:
            st.error(f"🔍 Toplam {len(df)} adet tutarsızlık bulundu:")
            st.table(df)
        else:
            st.success("✅ Tebrikler! Metin ve Kaynakça %100 uyumlu görünüyor.")
    else:
        st.error("Dosyada 'References' veya 'Kaynakça' başlığı tespit edilemedi.")

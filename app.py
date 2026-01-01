import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Kesin Sonuç", layout="wide")
st.title("🔍 Atıf & Kaynakça Çapraz Denetçi")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        
        # Metin temizleme (PDF karakter hatalarını onarır)
        full_text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', full_text)
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. KAYNAKÇA AYIRMA
    ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE))
    
    if ref_matches:
        split_point = ref_matches[-1].start()
        body_text = full_text[:split_point]
        ref_section = full_text[split_point:]

        # 2. KAYNAKÇADAKİ ESERLERİ BUL
        ref_entries = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_section)

        # 3. METİN İÇİ ATIFLARI BUL
        body_citations = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+)\s*\((\d{4}[a-z]?)\)', body_text)

        # GÜVENLİK KONTROLÜ: Eğer kod metinde hiç atıf bulamadıysa bir sorun var demektir
        if len(body_citations) == 0:
            st.warning("⚠️ Uyarı: Metin içerisinde hiç atıf (Örn: Yazar (2020)) tespit edilemedi. Lütfen PDF formatını kontrol edin.")
        
        errors = []

        # DENETİM: Kaynakçada var, Metinde yok (Hyland, Perkins, Swales vb.)
        for r_auth, r_year in ref_entries:
            # Metinde yazar ve yıl yan yana mı? (En esnek arama)
            found = re.search(rf"{r_auth}.{{0,50}}{r_year}", body_text, re.IGNORECASE)
            
            if not found:
                errors.append({
                    "Eser": f"{r_auth} ({r_year})",
                    "Hata": "⚠️ Metinde Atıfı Yok",
                    "Açıklama": "Bu kaynak listede var ama metinden sildiğiniz için bulunamadı."
                })

        # DENETİM: Metinde var, Kaynakçada yok (Biggs & Tang vb.)
        for b_auth, b_year in body_citations:
            b_clean = b_auth.replace(" et al.", "").replace("&", " ").split()[0].strip()
            if b_clean.lower() in ["table", "figure", "appendix"]: continue
            
            in_ref = re.search(rf"{b_clean}.*?{b_year}", ref_section, re.IGNORECASE)
            if not in_ref:
                errors.append({
                    "Eser": f"{b_auth} ({b_year})",
                    "Hata": "❌ Kaynakçada Kaydı Yok",
                    "Açıklama": "Metinde atıf var ama kaynakça listesinde eksik."
                })

        # ÇIKTI
        st.divider()
        df_errors = pd.DataFrame(errors).drop_duplicates()
        if not df_errors.empty:
            st.error(f"🔍 {len(df_errors)} Tutarsızlık Tespit Edildi:")
            st.table(df_errors)
        else:
            st.success("✅ Metin ve Kaynakça tam uyumlu!")
    else:
        st.error("Kaynakça bölümü tespit edilemedi.")

import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi", layout="wide")
st.title("🔍 Atıf & Kaynakça Denetçisi (Kararlı Sürüm)")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        
        # Metni temizle ama yapısal boşlukları koru
        clean_text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', full_text)

    # 1. KAYNAKÇA AYIRIMI (En sondaki References kelimesinden sonraki ilk harfe odaklan)
    ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', clean_text, re.IGNORECASE))
    
    if ref_matches:
        split_point = ref_matches[-1].end() # Kelimenin bittiği yerden başla
        body_text = clean_text[:ref_matches[-1].start()]
        ref_section = clean_text[split_point:]

        # 2. KAYNAKÇADAKİ ESERLERİ BUL (Hyland, Perkins, Swales...)
        # "Soyadı, A. (Yıl)" formatını yakalar, "References" kelimesine bakmaz
        ref_entries = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_section)

        # 3. METİN İÇİNDEKİ TÜM ATIFLARI BUL (Biggs & Tang, Zhai vb.)
        # Parantez içindeki (Yazar, 2023) veya Yazar (2023) kalıpları
        body_cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ&, ]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)

        errors = []

        # --- KONTROL A: KAYNAKÇADA VAR -> METİNDE YOK (Sildikleriniz) ---
        for r_auth, r_year in ref_entries:
            # "References" kelimesini yazar sanmasın diye ek kontrol
            if r_auth.lower() in ["references", "kaynakça"]: continue
            
            # Metin içinde soyadı ve yılı ara
            if not re.search(rf"\b{r_auth}\b.*?{r_year}", body_text, re.IGNORECASE):
                errors.append({
                    "Eser": f"{r_auth} ({r_year})",
                    "Hata Türü": "⚠️ Metinde Atıfı Yok",
                    "Detay": "Kaynakçada duruyor ama metin gövdesinden silinmiş."
                })

        # --- KONTROL B: METİNDE VAR -> KAYNAKÇADA YOK (Unutulanlar) ---
        for b_auth, b_year in body_cites:
            # Soyadını temizle (et al, & ve virgülleri at)
            b_clean = b_auth.replace(" et al.", "").replace("&", " ").replace(",", " ").split()[0].strip()
            
            # Gereksiz kelimeleri ele
            if b_clean.lower() in ["table", "figure", "appendix", "references", "source"]: continue
            if len(b_clean) < 3: continue
            
            # Kaynakçada bu soyadı ve yılı ara
            if not re.search(rf"\b{b_clean}\b.*?{b_year}", ref_section, re.IGNORECASE):
                errors.append({
                    "Eser": f"{b_auth.strip()} ({b_year})",
                    "Hata Türü": "❌ Kaynakçada Kaydı Yok",
                    "Detay": "Metinde bu esere atıf yapılmış ama kaynakça listesinde eksik."
                })

        # SONUÇLARI GÖSTER
        st.divider()
        df_errors = pd.DataFrame(errors).drop_duplicates()
        
        if not df_errors.empty:
            st.error(f"Toplam {len(df_errors)} adet tutarsızlık bulundu:")
            st.table(df_errors)
        else:
            st.success("Tebrikler! Metin ve Kaynakça tam uyumlu görünüyor.")

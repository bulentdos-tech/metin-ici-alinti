import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi", layout="wide")
st.title("🔍 Atıf & Kaynakça Denetçisi")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Dosya okunuyor, lütfen bekleyin...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        
        # Metni stabilize et
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. KAYNAKÇA AYIRIMI
    # En sondaki References kelimesini bul ve metni oradan böl
    ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE))
    
    if ref_matches:
        split_point = ref_matches[-1].start()
        body_text = full_text[:split_point]
        ref_section = full_text[split_point:]

        # 2. KAYNAKÇADAKİ ESERLERİ BUL (Hyland, Perkins, Swales...)
        # References kelimesini hariç tutarak "Soyadı, A. (Yıl)" kalıbını ara
        ref_entries = re.findall(r'(?!\b(?:References|Kaynakça)\b)\b([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_section)

        # 3. METİN İÇİNDEKİ TÜM ATIFLARI BUL (Biggs & Tang, Zhai vb.)
        # Parantez içindeki (Yazar, 2023) veya Yazar (2023) kalıpları
        body_cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ&, ]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)

        errors = []

        # --- KONTROL A: KAYNAKÇADA VAR -> METİNDE YOK (Sildikleriniz) ---
        for r_auth, r_year in ref_entries:
            # Metin içinde soyadı ve yılı ara
            if not re.search(rf"\b{r_auth}\b.*?{r_year}", body_text, re.IGNORECASE):
                errors.append({
                    "Eser": f"{r_auth} ({r_year})",
                    "Hata": "⚠️ Metinde Atıfı Yok",
                    "Detay": "Kaynakçada var ama metinde bulunamadı."
                })

        # --- KONTROL B: METİNDE VAR -> KAYNAKÇADA YOK (Unutulanlar) ---
        for b_auth, b_year in body_cites:
            # Soyadını temizle (et al, & ve virgülleri at)
            b_clean = b_auth.replace(" et al.", "").replace("&", " ").replace(",", " ").split()[0].strip()
            
            # Tablo/Şekil gibi kelimeleri ele
            if b_clean.lower() in ["table", "figure", "appendix", "references"]: continue
            
            # Kaynakçada bu soyadı ve yılı ara
            if not re.search(rf"\b{b_clean}\b.*?{b_year}", ref_section, re.IGNORECASE):
                errors.append({
                    "Eser": f"{b_auth.strip()} ({b_year})",
                    "Hata": "❌ Kaynakçada Yok",
                    "Detay": "Metinde atıf var ama kaynakça listesinde eksik."
                })

        # SONUÇLARI GÖSTER
        st.divider()
        df_errors = pd.DataFrame(errors).drop_duplicates()
        
        if not df_errors.empty:
            st.error(f"Toplam {len(df_errors)} tutarsızlık bulundu:")
            st.table(df_errors)
        else:
            st.success("Tebrikler! Metin ve Kaynakça tam uyumlu.")
    else:
        st.error("Kaynakça başlığı bulunamadı.")

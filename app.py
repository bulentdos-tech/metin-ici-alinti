import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Stabil", layout="wide")

st.title("🔍 Atıf Denetçisi (Stabil Sürüm)")
st.info("Bu sürüm sadece metin içinde atıf yapılıp kaynakçaya eklenmeyen eserleri listeler.")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " "
        doc.close()

        # Metni temizle (satır sonlarını ve boşlukları düzelt)
        full_text = re.sub(r'\s+', ' ', full_text)

        # 1. ADIM: KAYNAKÇA BÖLÜMÜNÜ AYIR
        # 'References' kelimesinin geçtiği yeri bul (Metin içinde atıf aramayı oraya kadar yapacağız)
        ref_header = re.search(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE)
        
        if ref_header:
            body_text = full_text[:ref_header.start()]
            ref_section = full_text[ref_header.start():]
            
            # 2. ADIM: METİN İÇİNDEKİ TÜM ATIFLARI BUL
            # Kalıp: (Yazar, 2020) veya Yazar (2020)
            # Bu regex 'Biggs & Tang (2011)' gibi yapıları da yakalar.
            cites_in_body = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+)\s*\((\d{4}[a-z]?)\)', body_text)
            
            results = []
            
            # 3. ADIM: HER ATIF KAYNAKÇADA VAR MI KONTROL ET
            for author, year in cites_in_body:
                # Temizlik: "Biggs & Tang" -> "Biggs"
                clean_author = author.replace(" et al.", "").replace("&", " ").split()[0].strip()
                
                # Kara liste (Atıf olmayan kelimeleri ele)
                if clean_author.lower() in ["table", "figure", "appendix", "chatgpt", "ai"]:
                    continue
                
                # Kaynakça kısmında bu yazarın soyadı ve yılı geçiyor mu?
                # Case-insensitive (Büyük/Küçük harf duyarsız) arama
                found = re.search(rf"{clean_author}.*?{year}", ref_section, re.IGNORECASE)
                
                if not found:
                    results.append({
                        "Metindeki Atıf": f"{author.strip()} ({year})",
                        "Durum": "❌ Kaynakçada Yok",
                        "Açıklama": "Bu eser metin içinde kullanılmış fakat kaynakça listesinde bulun

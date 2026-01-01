import streamlit as st
import pandas as pd
import re
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Gelişmiş Akademik Atıf Denetçisi")
st.markdown("Hatalı tarih eşleşmelerini (Örn: March 2020) eleyen ve satır sonu kaymalarını düzelten sürüm.")

# Ay isimleri ve akademik olmayan kelimeleri filtrelemek için liste
STOP_WORDS = [
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
    "ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık",
    "figure", "table", "page", "şekil", "tablo", "sayfa", "p.", "pp."
]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Metin temizleniyor ve analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            text = page.get_text("text")
            text = re.sub(r'-\s*\n', '', text) # Tireleri birleştir
            text = text.replace('\n', ' ')     # Satır sonlarını boşluk yap (Bogoch'u yakalamak için)
            full_text += text + " "
        doc.close()
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakça Bölümünü Ayır
    ref_keywords = [r'\bKaynakça\b', r'\bReferences\b', r'\bKAYNAKÇA\b', r'\bREFERENCES\b']
    split_index = -1
    for kw in ref_keywords:
        matches = list(re.finditer(kw, full_text, re.IGNORECASE))
        if matches:
            split_index = matches[-1].start()
            break

    if split_index != -1:
        body_text = full_text[:split_index]
        ref_text = full_text[split_index:].lower()

        # 2. Atıf Ayıklama (Geliştirilmiş Mantık)
        # Parantez içindeki grupları ve metin içi atıfları topla
        found_raw = []
        
        # Desen 1: Parantez içi çoklu veya tekli (Yazar, 2020; Yazar, 2021)
        paren_groups = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        for group in paren_groups:
            for sub in group.split(';'):
                found_raw.append(sub.strip())
        
        # Desen 2: Metin içi Yazar (2020)
        inline_matches = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        for auth, yr in inline_matches:
            found_raw.append(f"{auth} ({yr})")

        results = []
        for item in found_raw:
            # FİLTRELEME: Eğer içinde ay ismi veya yasaklı kelime varsa atla
            if any(stop.lower() in item.lower() for stop in STOP_WORDS):
                continue
            
            year_match = re.search(r'\d{4}', item)
            if not year_match: continue
            year = year_match.group()
            
            # Yazarları bul
            authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+|[A-ZÇĞİÖŞÜ]{2,}', item)
            
            if authors:
                # Akıllı eşleşme (Yazarlardan biri ve yıl kaynakçada var mı?)
                is_found = any(a.lower() in ref_text for a in authors) and year in ref_text
                
                results.append({
                    "Atıf": item,
                    "Yazar(lar)": ", ".join(authors),
                    "Yıl": year,
                    "Durum": "✅ Kaynakçada Var" if is_found else "❌ Kaynakçada Yok"
                })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Atıf'])

        # 3. Arayüz ve Çıktı
        st.subheader("Atıf Analiz Tablosu")
        st.dataframe(df_res, use_container_width=True)
        
        # Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res.to_excel(writer, index=False)
        
        st.download_button("📊 Raporu Excel Olarak İndir", output.getvalue(), "denetim_raporu.xlsx")
    else:
        st.error("Kaynakça tespit edilemedi.")

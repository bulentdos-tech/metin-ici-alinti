import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Kesinleştirilmiş Atıf Denetçisi")
st.markdown("Hatalı India/March eşleşmelerini eleyen, Bogoch gibi satır kaymalarını düzelten profesyonel sürüm.")

# Gelişmiş Kara Liste (Yazar soyadı olamayacak kelimeler)
KARA_LISTE = [
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
    "ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık",
    "india", "lockdown", "university", "school", "department", "figure", "table", "source", "adapted", "from", "although", "though",
    "the", "this", "that", "these", "those"
]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            text = page.get_text("text")
            text = re.sub(r'-\s*\n', '', text) # Satır sonu tire birleştir
            text = text.replace('\n', ' ')     # Satır sonlarını boşluk yap
            full_text += text + " "
        doc.close()
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakçayı Bul ve Ayır
    ref_keywords = [r'\bKaynakça\b', r'\bReferences\b', r'\bKAYNAKÇA\b']
    split_index = -1
    for kw in ref_keywords:
        matches = list(re.finditer(kw, full_text, re.IGNORECASE))
        if matches:
            split_index = matches[-1].start()
            break

    if split_index != -1:
        body_text = full_text[:split_index]
        ref_text = full_text[split_index:].lower()

        # 2. Atıf Ayıklama (Daha Hassas Regex)
        found_raw = []
        # Parantez içi: (Yazar, 2020)
        paren_groups = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        for group in paren_groups:
            for sub in group.split(';'):
                found_raw.append({"text": sub.strip(), "type": "Parantez İçi"})
        
        # Metin içi: Yazar (2020)
        inline_matches = re.finditer(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        for m in inline_matches:
            found_raw.append({"text": f"{m.group(1)} ({m.group(2)})", "type": "Metin İçi"})

        results = []
        for item in found_raw:
            raw_text = item["text"]
            
            # --- FİLTRELEME ADIMLARI ---
            # 1. Kara liste kontrolü
            if any(word.lower() in raw_text.lower().split() for word in KARA_LISTE):
                continue
            
            # 2. Yıl ve Yazarları bul
            year_match = re.search(r'\d{4}', raw_text)
            if not year_match: continue
            year = year_match.group()
            
            authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+|[A-ZÇĞİÖŞÜ]{2,}', raw_text)
            
            # 3. Yazar sayısı ve anlamsız kısa kelime kontrolü
            authors = [a for a in authors if len(a) > 2] # "In", "As" gibi kelimeleri ele
            
            if authors:
                # Eşleşme kontrolü
                is_found = any(a.lower() in ref_text for a in authors) and year in ref_text
                
                results.append({
                    "Metindeki Atıf": raw_text,
                    "Yazarlar": ", ".join(authors),
                    "Yıl": year,
                    "Tür": item["type"],
                    "Durum": "✅ Kaynakçada Var" if is_found else "❌ Kaynakçada Yok"
                })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Metindeki Atıf'])

        # 3. Arayüz
        st.subheader("Atıf Analiz Raporu")
        st.dataframe(df_res, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res.to_excel(writer, index=False)
        st.download_button("📊 Excel Raporu İndir", output.getvalue(), "denetim_raporu.xlsx")
    else:
        st.error("Kaynakça bölümü bulunamadı.")

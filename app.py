import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Profesyonel Atıf & Kaynakça Denetçisi")
st.markdown("Bu sürümde eşleşen kaynaklar tam metin olarak Excel'e eklenir ve sayfa sonunda listelenir.")

KARA_LISTE = [
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
    "ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık",
    "india", "lockdown", "university", "school", "department", "figure", "table", "source", "adapted", "from", "although", "though"
]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            text = page.get_text("text")
            text = re.sub(r'-\s*\n', '', text)
            text = text.replace('\n', ' ')
            full_text += text + " "
        doc.close()
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakçayı Bul ve Parçala
    ref_keywords = [r'\bKaynakça\b', r'\bReferences\b', r'\bKAYNAKÇA\b']
    split_index = -1
    for kw in ref_keywords:
        matches = list(re.finditer(kw, full_text, re.IGNORECASE))
        if matches:
            split_index = matches[-1].start()
            break

    if split_index != -1:
        body_text = full_text[:split_index]
        raw_ref_section = full_text[split_index:]
        
        # Kaynakçayı tekil kaynaklara bölmeye çalış (Genellikle (Yıl) veya Soyad ile ayrılır)
        # Basit bir yöntem: Her kaynağı yazar soyadlarından tahmin etmeye çalışalım
        # Şimdilik karşılaştırma için kaynakçayı cümle cümle veya blok blok saklayalım
        ref_blocks = re.split(r'(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,\s[A-Z]\.)', raw_ref_section)

        # 2. Atıf Ayıklama
        found_raw = []
        paren_groups = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        for group in paren_groups:
            for sub in group.split(';'):
                found_raw.append({"text": sub.strip(), "type": "Parantez İçi"})
        
        inline_matches = re.finditer(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        for m in inline_matches:
            found_raw.append({"text": f"{m.group(1)} ({m.group(2)})", "type": "Metin İçi"})

        results = []
        for item in found_raw:
            raw_text = item["text"]
            if any(word.lower() in raw_text.lower().split() for word in KARA_LISTE):
                continue
            
            year_match = re.search(r'\d{4}', raw_text)
            if not year_match: continue
            year = year_match.group()
            
            authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+|[A-ZÇĞİÖŞÜ]{2,}', raw_text)
            authors = [a for a in authors if len(a) > 2]
            
            if authors:
                matched_ref_text = "Bulunamadı"
                is_found = False
                
                # Kaynakçada bu atıfın tam metnini ara
                for block in ref_blocks:
                    if any(a.lower() in block.lower() for a in authors) and year in block:
                        matched_ref_text = block.strip()
                        is_found = True
                        break
                
                results.append({
                    "Metindeki Atıf": raw_text,
                    "Yazarlar": ", ".join(authors),
                    "Yıl": year,
                    "Durum": "✅ Var" if is_found else "❌ Yok",
                    "Kaynakçadaki Tam Metni": matched_ref_text
                })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Metindeki Atıf'])

        # 3. Arayüz ve Excel
        st.subheader("📊 Atıf ve Kaynakça Karşılaştırma Tablosu")
        st.dataframe(df_res, use_container_width=True)
        
        # Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res.to_excel(writer, index=False)
        st.download_button("📥 Excel Raporunu İndir", output.getvalue(), "atik_kaynakca_denetimi.xlsx")

        # 4. Sayfa Altına Tüm Kaynakçayı Listele
        st.divider()
        st.subheader("📚 Tespit Edilen Kaynakça Listesi")
        with st.expander("Tüm Kaynakçayı Görüntüle"):
            for i, block in enumerate(ref_blocks):
                if len(block.strip()) > 10:
                    st.write(f"**[{i}]** {block.strip()}")
    else:
        st.error("Kaynakça bölümü tespit edilemedi.")

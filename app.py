import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Kesinleştirilmiş Atıf & Kaynakça Denetçisi")
st.markdown("Bu sürümde kaynakça parçalama mantığı optimize edildi ve Excel çıktısı güçlendirildi.")

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
            text = text.replace('\n', ' [NL] ') # Satır sonlarını işaretle (ayrıştırma için)
            full_text += text + " "
        doc.close()
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakça Bölümünü Tespit Et
    ref_keywords = [r'Kaynakça', r'References', r'KAYNAKÇA', r'REFERENCES', r'Kaynaklar']
    split_index = -1
    for kw in ref_keywords:
        # Kelime sınırı olmadan ara (bitişik yazılmış olabilir)
        match = re.search(kw, full_text)
        if match:
            # Genelde kaynakça sondadır, son eşleşmeyi bulalım
            all_matches = list(re.finditer(kw, full_text))
            split_index = all_matches[-1].start()
            break

    if split_index != -1:
        body_text = full_text[:split_index]
        raw_ref_section = full_text[split_index:]
        
        # Kaynakçayı her bir kaynak için parçalara ayır
        # Genellikle her kaynak [NL] (yeni satır) ile başlar
        ref_blocks = [b.replace('[NL]', '').strip() for b in raw_ref_section.split(' [NL] ') if len(b.strip()) > 20]

        # 2. Atıf Ayıklama
        found_raw = []
        # Parantez içi
        paren_groups = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        for group in paren_groups:
            for sub in group.split(';'):
                found_raw.append({"text": sub.strip(), "type": "Parantez İçi"})
        
        # Metin içi
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
                matched_full_ref = "KAYNAKÇADA BULUNAMADI"
                is_found = False
                
                # Kaynakçadaki her bloğu kontrol et
                for block in ref_blocks:
                    if any(a.lower() in block.lower() for a in authors) and year in block:
                        matched_full_ref = block
                        is_found = True
                        break
                
                results.append({
                    "Metindeki Atıf": raw_text,
                    "Yazarlar": ", ".join(authors),
                    "Yıl": year,
                    "Durum": "✅ Var" if is_found else "❌ Yok",
                    "Kaynakçadaki Tam Karşılığı": matched_full_ref
                })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Metindeki Atıf'])

        # 3. Görselleştirme
        st.subheader("📊 Atıf & Kaynakça Eşleşme Raporu")
        st.dataframe(df_res, use_container_width=True)
        
        # Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res.to_excel(writer, index=False)
        st.download_button("📥 Excel Raporunu İndir", output.getvalue(), "denetim_sonuclari.xlsx")

        # 4. Kaynakça Önizleme ve Liste
        st.divider()
        st.subheader("📚 Ayıklanan Kaynakça Maddeleri")
        with st.expander("PDF'den ayrıştırılan tüm kaynakları gör"):
            if ref_blocks:
                for b in ref_blocks:
                    st.markdown(f"- {b}")
            else:
                st.warning("Kaynakça başlığı bulundu ama maddeler ayrıştırılamadı.")
                st.text("Ham Metin Önizlemesi:")
                st.write(raw_ref_section[:1000])
    else:
        st.error("Kaynakça bölümü (References/Kaynakça) tespit

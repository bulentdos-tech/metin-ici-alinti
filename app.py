import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Profesyonel Atıf Denetçisi")
st.markdown("Metin ve Kaynakça arasındaki tutarsızlıkları (eksik veya fazla kaynaklar) raporlar.")

KARA_LISTE = ["march", "april", "university", "journal", "retrieved", "from", "doi", "http", "https", "pdf", "page", "january"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Dosya analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " \n "
        doc.close()
        full_text = re.sub(r'[ \t]+', ' ', full_text)

    # 1. Kaynakça Bölümünü Ayır
    ref_keywords = [r'\bReferences\b', r'\bKaynakça\b', r'\bKAYNAKÇA\b']
    split_index = -1
    for kw in ref_keywords:
        matches = list(re.finditer(kw, full_text, re.IGNORECASE))
        if matches:
            split_index = matches[-1].start()
            break

    if split_index != -1:
        body_text = full_text[:split_index]
        raw_ref_section = full_text[split_index:].replace('References', '').replace('Kaynakça', '')
        
        # Kaynakça bloklarını bölme
        pattern = r'\.\s+(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)'
        ref_blocks = [b.strip() for b in re.split(pattern, raw_ref_section) if len(b.strip()) > 15]

        # --- ANALİZ 1: METİNDE VAR, KAYNAKÇADA YOK ---
        found_raw = []
        # Parantez içi: (Yazar, 2020)
        paren_groups = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        for group in paren_groups:
            for sub in group.split(';'):
                found_raw.append(sub.strip())
        
        # Metin içi: Yazar (2020)
        inline_matches = re.finditer(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        for m in inline_matches:
            found_raw.append(f"{m.group(1)} ({m.group(2)})")

        text_to_ref_errors = []
        for item in found_raw:
            if any(word in item.lower() for word in KARA_LISTE): continue
            
            year_match = re.search(r'\d{4}', item)
            if not year_match: continue
            year = year_match.group()
            
            authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', item)
            authors = [a for a in authors if len(a) > 2 and a.lower() not in KARA_LISTE]
            
            if authors:
                main_author = authors[0]
                # Sadece kaynakçada bulunamayanları listeye ekle
                is_found = any(main_author.lower() in block.lower() and year in block for block in ref_blocks)
                
                if not is_found:
                    text_to_ref_errors.append({"Tespit Edilen Atıf": item})

        df_missing_in_ref = pd.DataFrame(text_to_ref_errors).drop_duplicates()

        # --- ANALİZ 2: KAYNAKÇADA VAR, METİNDE YOK ---
        ref_to_text_errors = []
        for block in ref_blocks:
            ref_author_match = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', block)
            ref_year_match = re.search(r'(\d{4})', block)
            
            if ref_author_match and ref_year_match:
                author = ref_author_match.group(1)
                year = ref_year_match.group(1)
                
                is_cited = (author.lower() in body_text.lower()) and (year in body_text)
                
                if not is_cited:
                    # Kaynakçayı tam vermemek için sadece ilk 100 karakteri gösteriyoruz
                    ref_to_text_errors.append({"Atıfı Olmayan Kaynak (Özet)": block[:100] + "..."})

        df_unused_refs = pd.DataFrame(ref_to_text_errors)

        # --- SONUÇLARI GÖSTER ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("❌ Kaynakçada Bulunmayanlar")
            if not df_missing_in_ref.empty:
                st.info("Metinde kullanılmış ancak kaynakça listesine eklenmemiş:")
                st.table(df_missing_in_ref)
            else:
                st.success("Tebrikler! Metindeki tüm atıflar kaynakçada mevcut.")

        with col2:
            st.subheader("⚠️ Metinde Atıfı Olmayanlar")
            if not df_unused_refs.empty:
                st.info("Kaynakça listesinde var ancak metinde atıfı bulunamadı:")
                st.table(df_unused_refs)
            else:
                st.success("Tebrikler! Kaynakçadaki tüm eserlere metin içinde atıf yapılmış.")

        # Excel Raporu Hazırlama
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if not df_missing_in_ref.empty:
                df_missing_in_ref.to_excel(writer, sheet_name='Eksik Kaynaklar', index=False)
            if not df_unused_refs.empty:
                df_unused_refs.to_excel(writer, sheet_name='Gereksiz Kaynaklar', index=False)
        
        st.divider()
        st.download_button("📥 Hata Raporunu Excel Olarak İndir", output.getvalue(), "denetim_raporu.xlsx")

    else:
        st.error("Kaynakça/References başlığı bulunamadığı için karşılaştırma yapılamadı.")

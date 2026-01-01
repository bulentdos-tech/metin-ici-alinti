import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Profesyonel Atıf Denetçisi (Karşılıklı Kontrol)")
st.markdown("Bu sürüm metin ve kaynakça arasındaki tutarsızlıkları çift yönlü olarak denetler.")

KARA_LISTE = ["march", "april", "university", "journal", "retrieved", "from", "doi", "http", "https", "pdf", "page", "january"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Metin ve Kaynakça analiz ediliyor...'):
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
        
        # Kaynakça bloklarını bölme (Soyadı, A. formatına göre)
        pattern = r'\.\s+(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)'
        ref_blocks = [b.strip() for b in re.split(pattern, raw_ref_section) if len(b.strip()) > 15]

        # --- ANALİZ 1: METİN İÇİ ATIFLARIN KAYNAKÇADA KONTROLÜ ---
        found_raw = []
        # (Yazar, 2020) tipi
        paren_groups = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        for group in paren_groups:
            for sub in group.split(';'):
                found_raw.append(sub.strip())
        
        # Yazar (2020) tipi
        inline_matches = re.finditer(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        for m in inline_matches:
            found_raw.append(f"{m.group(1)} ({m.group(2)})")

        text_to_ref_results = []
        for item in found_raw:
            if any(word in item.lower() for word in KARA_LISTE): continue
            
            year_match = re.search(r'\d{4}', item)
            if not year_match: continue
            year = year_match.group()
            
            authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', item)
            authors = [a for a in authors if len(a) > 2 and a.lower() not in KARA_LISTE]
            
            if authors:
                main_author = authors[0]
                is_found = any(main_author.lower() in block.lower() and year in block for block in ref_blocks)
                
                text_to_ref_results.append({
                    "Metindeki Atıf": item,
                    "Ana Yazar": main_author,
                    "Yıl": year,
                    "Durum": "✅ Kaynakçada Var" if is_found else "❌ Kaynakçada Yok"
                })

        df_missing_in_ref = pd.DataFrame(text_to_ref_results).drop_duplicates(subset=['Metindeki Atıf'])

        # --- ANALİZ 2: KAYNAKÇADAKİLERİN METİNDE KONTROLÜ ---
        ref_to_text_results = []
        for block in ref_blocks:
            # Bloktan yazar ve yıl ayıklama denemesi
            ref_author_match = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', block)
            ref_year_match = re.search(r'(\d{4})', block)
            
            if ref_author_match and ref_year_match:
                author = ref_author_match.group(1)
                year = ref_year_match.group(1)
                
                # Metinde bu yazar ve yıl geçiyor mu?
                is_cited = (author.lower() in body_text.lower()) and (year in body_text)
                
                if not is_cited:
                    ref_to_text_results.append({
                        "Kaynakçadaki Eser (Kısa)": block[:100] + "...",
                        "Yazar": author,
                        "Yıl": year,
                        "Durum": "⚠️ Metinde Atıfı Yok"
                    })

        df_unused_refs = pd.DataFrame(ref_to_text_results)

        # --- SONUÇLARIN GÖSTERİLMESİ ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🚩 Kaynakçada Olmayan Atıflar")
            missing = df_missing_in_ref[df_missing_in_ref["Durum"] == "❌ Kaynakçada Yok"]
            if not missing.empty:
                st.dataframe(missing[["Metindeki Atıf", "Durum"]], use_container_width=True)
            else:
                st.success("Metindeki tüm atıflar kaynakçada mevcut.")

        with col2:
            st.subheader("🚩 Metinde Atıfı Olmayan Kaynaklar")
            if not df_unused_refs.empty:
                st.dataframe(df_unused_refs[["Kaynakçadaki Eser (Kısa)", "Durum"]], use_container_width=True)
            else:
                st.success("Kaynakçadaki tüm eserlere metin içinde atıf yapılmış.")

        # Excel Raporu
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_missing_in_ref.to_excel(writer, sheet_name='Metinden Kaynakçaya', index=False)
            df_unused_refs.to_excel(writer, sheet_name='Kaynakçadan Metne', index=False)
        st.download_button("📥 Tam Denetim Raporunu İndir (Excel)", output.getvalue(), "denetim_sonucu.xlsx")

    else:
        st.error("Kaynakça başlığı bulunamadı. Lütfen PDF'de 'References' veya 'Kaynakça' başlığı olduğundan emin olun.")

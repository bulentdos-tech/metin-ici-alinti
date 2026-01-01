import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Profesyonel Atıf Denetçisi (Hatasız Sürüm)")
st.markdown("Bu sürüm, kaynakçadaki bir ismi sadece **metin gövdesinde** arar; kaynakçanın kendisini tarama dışı bırakır.")

KARA_LISTE = ["march", "april", "university", "journal", "retrieved", "from", "doi", "http", "https", "pdf", "page", "january", "study", "research"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Derinlemesine analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " \n "
        doc.close()
        # Metin temizleme
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakça Bölümünü Ayır (Arama alanını kısıtlamak için kritik)
    ref_keywords = [r'\bReferences\b', r'\bKaynakça\b', r'\bKAYNAKÇA\b']
    split_index = -1
    for kw in ref_keywords:
        matches = list(re.finditer(kw, full_text, re.IGNORECASE))
        if matches:
            split_index = matches[-1].start()
            break

    if split_index != -1:
        # Sadece kaynakçadan önceki metin
        body_text = full_text[:split_index]
        # Sadece kaynakça metni
        raw_ref_section = full_text[split_index:]
        
        # Kaynakçayı bloklara böl (APA ve genel formatlar için optimize edildi)
        ref_pattern = r'(?<=\d{4}[a-z]?\)\. )|(?<=\.\s)(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)'
        ref_blocks = [b.strip() for b in re.split(ref_pattern, raw_ref_section) if len(b.strip()) > 15]

        # --- ANALİZ 1: METİNDE VAR, KAYNAKÇADA YOK ---
        found_in_body = []
        # Parantez içi: (Yazar, 2020)
        paren_matches = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        for group in paren_matches:
            for sub in group.split(';'):
                found_in_body.append(sub.strip())
        
        # Metin içi: Yazar (2020)
        inline_matches = re.finditer(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        for m in inline_matches:
            found_in_body.append(f"{m.group(1)} ({m.group(2)})")

        text_to_ref_errors = []
        for item in found_in_body:
            if any(word in item.lower() for word in KARA_LISTE): continue
            year_m = re.search(r'\d{4}', item)
            if not year_m: continue
            year = year_m.group()
            
            # Yazarı çek (Örn: "Zhai" veya "Biggs")
            authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', item)
            if authors:
                main_author = authors[0]
                # SADECE kaynakça blokları içinde ara
                is_in_ref = any(main_author.lower() in block.lower() and year in block for block in ref_blocks)
                if not is_in_ref:
                    text_to_ref_errors.append({"Tespit Edilen Atıf": item})

        df_missing_in_ref = pd.DataFrame(text_to_ref_errors).drop_duplicates()

        # --- ANALİZ 2: KAYNAKÇADA VAR, METİNDE YOK (Burada sildiğiniz kaynaklar çıkmalı) ---
        ref_to_text_errors = []
        for block in ref_blocks:
            # Kaynakça bloğundan ilk yazar ve yılı bul
            author_match = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', block)
            year_match = re.search(r'(\d{4})', block)
            
            if author_match and year_match:
                author = author_match.group(1)
                year = year_match.group(1)
                
                # KRİTİK: Sadece body_text (metin gövdesi) içinde ara!
                # (Yazar, 2020) veya Yazar (2020) kalıplarını kontrol et
                cit_pattern = rf"{author}.*?{year}|{year}.*?{author}"
                is_cited_in_body = re.search(cit_pattern, body_text, re.IGNORECASE)
                
                if not is_cited_in_body:
                    ref_to_text_errors.append({"Atıfı Olmayan Kaynak": block[:120] + "..."})

        df_unused_refs = pd.DataFrame(ref_to_text_errors)

        # --- SONUÇ EKRANI ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("❌ Kaynakçada Bulunmayan Atıflar")
            if not df_missing_in_ref.empty:
                st.error(f"{len(df_missing_in_ref)} eksik kaynak bulundu.")
                st.table(df_missing_in_ref)
            else:
                st.success("Metindeki tüm atıflar kaynakçada var.")

        with col2:
            st.subheader("⚠️ Metinde Atıfı Olmayan Kaynaklar")
            if not df_unused_refs.empty:
                st.warning(f"{len(df_unused_refs)} kaynak metinde kullanılmamış.")
                st.table(df_unused_refs)
            else:
                st.success("Kaynakçadaki tüm eserlere atıf yapılmış.")

        # Excel Raporu
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_missing_in_ref.to_excel(writer, sheet_name='Eksik Kaynaklar', index=False)
            df_unused_refs.to_excel(writer, sheet_name='Atıfı Olmayanlar', index=False)
        st.divider()
        st.download_button("📥 Hata Raporunu İndir", output.getvalue(), "denetim_raporu.xlsx")
    else:
        st.error("Kaynakça başlığı bulunamadı.")

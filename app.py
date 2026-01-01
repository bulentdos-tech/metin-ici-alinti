import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Profesyonel Atıf Denetçisi (Kesin Sonuç)")
st.markdown("Bu sürüm, kaynakçadaki eserleri **sadece metin gövdesinde** arar. Kaynakçanın kendisini tarama dışı bırakır.")

KARA_LISTE = ["march", "april", "university", "journal", "retrieved", "from", "doi", "http", "https", "pdf", "page", "january", "proceedings", "conference"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Dosya analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " \n "
        doc.close()
        
        # Metin normalizasyonu (Gereksiz boşlukları ve satır sonu kaymalarını temizler)
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakça Bölümünü Tespit Et ve Böl
    # 'References' veya 'Kaynakça' kelimesinin en son geçtiği yeri bul (İçindekiler kısmıyla karışmaması için)
    ref_keywords = [r'\bReferences\b', r'\bKaynakça\b', r'\bKAYNAKÇA\b']
    split_index = -1
    for kw in ref_keywords:
        matches = list(re.finditer(kw, full_text, re.IGNORECASE))
        if matches:
            # En sondaki 'References' başlığını al
            split_index = matches[-1].start()
            break

    if split_index != -1:
        # --- KRİTİK AYRIM ---
        body_text = full_text[:split_index]  # Sadece metin (Arama burada yapılacak)
        raw_ref_section = full_text[split_index:] # Sadece kaynakça listesi
        
        # Kaynakçayı bloklara ayır (Yazar, A. (Yıl) formatına göre)
        # Bu pattern 'Soyadı, A.' veya 'Soyadı, A. B.' şeklinde başlayan satırları yakalar
        ref_pattern = r'(?<=\.\s)(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)'
        ref_blocks = [b.strip() for b in re.split(ref_pattern, raw_ref_section) if len(b.strip()) > 20]

        # --- ANALİZ 1: METİNDE VAR, KAYNAKÇADA YOK ---
        found_in_body = []
        # (Yazar, 2020) veya Yazar (2020)
        matches = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        for auth, yr in matches:
            found_in_body.append({"auth": auth.strip(), "year": yr, "full": f"{auth} ({yr})"})

        missing_in_ref = []
        for cit in found_in_body:
            author_key = cit["auth"].split()[0].replace(',', '').lower()
            if any(word in author_key for word in KARA_LISTE): continue
            
            # Kaynakça blokları içinde bu yazar ve yılı ara
            is_in_ref = any(author_key in block.lower() and cit["year"] in block for block in ref_blocks)
            if not is_in_ref:
                missing_in_ref.append({"Metindeki Atıf": cit["full"]})

        df_missing_in_ref = pd.DataFrame(missing_in_ref).drop_duplicates()

        # --- ANALİZ 2: KAYNAKÇADA VAR, METİNDE YOK (Sizin sildiğiniz kaynaklar burada çıkacak) ---
        unused_refs = []
        for block in ref_blocks:
            # Bloğun başındaki Soyadı ve ilk yılı çek
            author_match = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', block)
            year_match = re.search(r'(\d{4})', block)
            
            if author_match and year_match:
                author_surname = author_match.group(1)
                ref_year = year_match.group(1)
                
                # ÖNEMLİ: Sadece body_text (metin gövdesi) içinde yazar ve yılı yan yana ara
                # Regex: Yazar isminden sonra makul bir mesafede yıl gelmeli
                check_pattern = rf"{author_surname}.*?{ref_year}|{ref_year}.*?{author_surname}"
                is_cited = re.search(check_pattern, body_text, re.IGNORECASE)
                
                if not is_cited:
                    unused_refs.append({"Metinde Atıfı Bulunmayan Kaynak": block[:120] + "..."})

        df_unused_refs = pd.DataFrame(unused_refs)

        # --- GÖRSELLEŞTİRME ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("❌ Kaynakçada Olmayan Atıflar")
            if not df_missing_in_ref.empty:
                st.error(f"{len(df_missing_in_ref)} atıf kaynakçada bulunamadı.")
                st.table(df_missing_in_ref)
            else:
                st.success("Tüm atıflar kaynakçada mevcut.")

        with col2:
            st.subheader("⚠️ Metinde Atıfı Olmayanlar")
            if not df_unused_refs.empty:
                st.warning(f"{len(df_unused_refs)} kaynak metinde hiç geçmiyor.")
                st.table(df_unused_refs)
            else:
                st.success("Kaynakçadaki tüm eserlere atıf yapılmış.")

        # Excel Raporu
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if not df_missing_in_ref.empty:
                df_missing_in_ref.to_excel(writer, sheet_name='Eksik Kaynaklar', index=False)
            if not df_unused_refs.empty:
                df_unused_refs.to_excel(writer, sheet_name='Metinde Atıfı Yok', index=False)
        
        st.divider()
        st.download_button("📥 Hata Raporunu İndir", output.getvalue(), "denetim_raporu.xlsx")

    else:
        st.error("Kaynakça/References başlığı bulunamadı.")

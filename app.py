import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Profesyonel Atıf Denetçisi (Gelişmiş Denetim)")
st.markdown("Bu sürüm, sadece metin içinde geçen kelimelere değil, gerçek atıf desenlerine odaklanır.")

KARA_LISTE = ["march", "april", "university", "journal", "retrieved", "from", "doi", "http", "https", "pdf", "page", "january"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Derinlemesine analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " \n "
        doc.close()
        full_text = re.sub(r'[ \t]+', ' ', full_text)

    # 1. Kaynakça Ayırma
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
        
        # Daha esnek bölme: Nokta + Boşluk + Büyük Harf ile başlayan bloklar
        pattern = r'\n(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)|\.\s+(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)'
        ref_blocks = [b.strip() for b in re.split(pattern, raw_ref_section) if len(b.strip()) > 10]

        # --- ANALİZ 1: METİNDE VAR, KAYNAKÇADA YOK ---
        # Önce tüm metin içi atıfları bir listeye alalım
        found_citations = []
        # (Yazar, 2020) veya Yazar (2020)
        matches = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+(?:\s+et\s+al\.)?)\s*\(?(\d{4}[a-z]?)\)?', body_text)
        for auth, yr in matches:
            if auth.lower() not in KARA_LISTE:
                found_citations.append({"auth": auth, "yr": yr, "full": f"{auth} ({yr})"})

        text_to_ref_errors = []
        for cit in found_citations:
            # Kaynakça bloklarının içinde bu yazar ve yıl var mı?
            is_found = any(cit["auth"].split()[0].lower() in block.lower() and cit["yr"] in block for block in ref_blocks)
            if not is_found:
                text_to_ref_errors.append({"Tespit Edilen Atıf": cit["full"]})

        df_missing_in_ref = pd.DataFrame(text_to_ref_errors).drop_duplicates()

        # --- ANALİZ 2: KAYNAKÇADA VAR, METİNDE YOK (Hassas Denetim) ---
        ref_to_text_errors = []
        for block in ref_blocks:
            # Kaynakça bloğundan yazar ve yılı daha dikkatli çek
            author_match = re.search(r'^([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)', block)
            year_match = re.search(r'(\d{4})', block)
            
            if author_match and year_match:
                author = author_match.group(1)
                year = year_match.group(1)
                
                # Sadece kelime olarak değil, bir atıf kalıbı içinde mi?
                # Örn: (Yılmaz, 2020) veya Yılmaz (2020) veya Yılmaz et al. (2020)
                citation_regex = rf"{author}.*?{year}|{year}.*?{author}"
                is_cited = re.search(citation_regex, body_text, re.IGNORECASE)
                
                if not is_cited:
                    ref_to_text_errors.append({"Atıfı Olmayan Kaynak": block[:120] + "..."})

        df_unused_refs = pd.DataFrame(ref_to_text_errors)

        # --- GÖRSELLEŞTİRME ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("❌ Kaynakçada Bulunmayanlar")
            if not df_missing_in_ref.empty:
                st.error("Aşağıdaki atıflar metinde var ama kaynakçada yok:")
                st.table(df_missing_in_ref)
            else:
                st.success("Tüm atıflar kaynakçada mevcut.")

        with col2:
            st.subheader("⚠️ Metinde Atıfı Olmayanlar")
            if not df_unused_refs.empty:
                st.warning("Aşağıdaki kaynaklar listede var ama metinde atıfı bulunamadı:")
                st.table(df_unused_refs)
            else:
                st.success("Tüm kaynaklara metinde atıf yapılmış.")

        # Excel Raporu
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_missing_in_ref.to_excel(writer, sheet_name='Eksik Kaynaklar', index=False)
            df_unused_refs.to_excel(writer, sheet_name='Atıfı Olmayanlar', index=False)
        st.divider()
        st.download_button("📥 Hata Raporunu İndir", output.getvalue(), "denetim_raporu.xlsx")

    else:
        st.error("Kaynakça/References başlığı bulunamadı.")

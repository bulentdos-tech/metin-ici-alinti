import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Kesin Sonuçlu Atıf Denetçisi")
st.markdown("Bu sürüm, kaynakçadaki eserleri **sadece metin gövdesinde** arar. Kaynakçanın kendisini tarama dışı bırakır.")

KARA_LISTE = ["university", "journal", "retrieved", "from", "doi", "http", "https", "page", "proceedings", "table", "figure"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " \n "
        doc.close()
        
        # Metni temizle ama yapıyı koru
        full_text = re.sub(r'[ \t]+', ' ', full_text)

    # 1. BÖLÜM: METİN VE KAYNAKÇAYI BIÇAKLA KESER GİBİ AYIR
    # 'References' kelimesinin en son geçtiği yeri bul (genelde son sayfalardadır)
    split_index = -1
    ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE))
    
    if ref_matches:
        # En sondaki eşleşmeyi al (İçindekiler kısmıyla karışmaması için)
        split_index = ref_matches[-1].start()

    if split_index != -1:
        # --- ÖNEMLİ AYRIM ---
        body_text = full_text[:split_index]  # SADECE BURADA ARAMA YAPACAĞIZ
        ref_text = full_text[split_index:]   # BURADAN KAYNAKLARI ÇEKECEĞİZ

        # 2. BÖLÜM: KAYNAKÇADAKİ ESERLERİ TESPİT ET
        # APA formatındaki 'Soyadı, A. (Yıl)' yapısını yakalar
        ref_blocks = re.split(r'\n(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)', ref_text)
        ref_blocks = [b.strip() for b in ref_blocks if len(b.strip()) > 15]

        missing_in_body = [] # Sildiğiniz kaynaklar buraya düşecek
        year_mismatch = []   # Zhai (2022) vs (2023) buraya düşecek

        for block in ref_blocks:
            # Bloktan yazar soyadını ve yılı çek
            # Örn: "Perkins, K. (2023)..." -> Soyad: Perkins, Yıl: 2023
            auth_match = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', block)
            year_match = re.search(r'\((\d{4})\)', block)
            
            if auth_match and year_match:
                soyad = auth_match.group(1)
                yil = year_match.group(1)
                
                # KRİTİK: Sadece body_text içinde tam kelime araması yap
                # \b (word boundary) çok önemli: 'Swales' ararken 'Sweller'ı bulmaz.
                pattern = rf"\b{soyad}\b"
                found_in_body = re.search(pattern, body_text, re.IGNORECASE)
                
                if not found_in_body:
                    # EĞER METİNDE HİÇ YOKSA (Sildiğiniz durum)
                    missing_in_body.append({"Kaynakçadaki Eser": f"{soyad} ({yil})"})
                else:
                    # İsim var ama yıl doğru mu? (Zhai hatası için)
                    # Yazar isminin geçtiği yerin yakınında o yıl var mı?
                    year_pattern = rf"{soyad}.*?{yil}|{yil}.*?{soyad}"
                    if not re.search(year_pattern, body_text, re.IGNORECASE | re.DOTALL):
                        # İsim var ama bu yılla hiç geçmiyor
                        # Metindeki mevcut yılı bulmaya çalış
                        actual_year = re.search(rf"{soyad}.*?(\d{{4}})", body_text, re.IGNORECASE | re.DOTALL)
                        metin_yili = actual_year.group(1) if actual_year else "Bulunamadı"
                        year_mismatch.append({
                            "Yazar": soyad,
                            "Kaynakçada": yil,
                            "Metinde": metin_yili
                        })

        # 3. BÖLÜM: METİNDE VAR KAYNAKÇADA YOK (Biggs & Tang vb.)
        missing_in_ref = []
        # Metin içi atıf kalıplarını bul: (Yazar, 2020) veya Yazar (2020)
        body_cits = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s*\((\d{4})\)', body_text)
        for b_auth, b_year in body_cits:
            if any(k in b_auth.lower() for k in KARA_LISTE): continue
            
            # Kaynakçada bu soyad ve yıl var mı?
            is_in_ref = any(b_auth.lower() in r_block.lower() and b_year in r_block for r_block in ref_blocks)
            if not is_in_ref:
                missing_in_ref.append({"Metindeki Atıf": f"{b_auth} ({b_year})"})

        # --- EKRAN ÇIKTILARI ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🚩 Metinde Atıfı Olmayanlar")
            df_missing = pd.DataFrame(missing_in_body).drop_duplicates()
            if not df_missing.empty:
                st.error("Aşağıdaki kaynaklar listede var ama metinde atıfı bulunamadı:")
                st.table(df_missing)
            else:
                st.success("Tüm kaynaklar metinde kullanılmış.")

        with col2:
            st.subheader("❌ Kaynakçada Olmayanlar")
            df_no_ref = pd.DataFrame(missing_in_ref).drop_duplicates()
            if not df_no_ref.empty:
                st.warning("Metinde atıfı var ama kaynakçada listelenmemiş:")
                st.table(df_no_ref)
            else:
                st.success("Tüm atıflar kaynakçada mevcut.")

        if year_mismatch:
            st.divider()
            st.subheader("📅 Yıl Uyuşmazlığı Tespit Edildi")
            st.info("İsim metinde geçiyor ancak yılı kaynakçadakinden farklı:")
            st.table(pd.DataFrame(year_mismatch).drop_duplicates())

    else:
        st.error("Kaynakça bölümü (References) tespit edilemedi. Lütfen başlığın 'References' veya 'Kaynakça' olduğundan emin olun.")

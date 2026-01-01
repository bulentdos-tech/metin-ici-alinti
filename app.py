import streamlit as st
import pandas as pd
import re
import fitz # PyMuPDF
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Kesin Sonuçlu Atıf Denetçisi")
st.markdown("Bu sürüm, kaynakçadaki eserleri **sadece metin gövdesinde** arar ve yıl uyuşmazlıklarını denetler.")

# Gereksiz kelimeleri filtrele
KARA_LISTE = ["university", "journal", "retrieved", "from", "doi", "http", "https", "page", "proceedings"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Dosya derinlemesine analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " \n "
        doc.close()
        
        # Metni temizle ama yapıyı bozma
        full_text = re.sub(r'[ \t]+', ' ', full_text)

    # 1. ADIM: METİN VE KAYNAKÇAYI BİRBİRİNDEN AYIR
    # Kaynakça genellikle dosyanın sonundadır. En sondaki 'References' başlığını bul.
    ref_basliklari = [r'\n\s*References\s*\n', r'\n\s*Kaynakça\s*\n', r'\n\s*KAYNAKÇA\s*\n']
    split_point = -1
    
    for pattern in ref_basliklari:
        matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
        if matches:
            split_point = matches[-1].start()
            break
            
    if split_point == -1:
        # Eğer özel başlık bulunamazsa 'References' kelimesinin geçtiği son yeri bul
        split_point = full_text.lower().rfind("references")

    if split_point != -1:
        body_text = full_text[:split_point]  # SADECE BURADA ARAMA YAPACAĞIZ
        ref_section = full_text[split_point:] # BURADAN KAYNAKLARI ÇEKECEĞİZ

        # 2. ADIM: KAYNAKÇADAKİ ESERLERİ AYIKLA
        # APA formatındaki 'Soyadı, A. (Yıl)' yapısını baz alır
        ref_blocks = re.split(r'\n(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)', ref_section)
        ref_blocks = [b.strip() for b in ref_blocks if len(b.strip()) > 15]

        missing_in_body = [] # Kaynakçada var, metinde yok
        wrong_year = []      # Yıl uyuşmazlığı

        for block in ref_blocks:
            # Bloktan soyadı ve yılı çek (Örn: Hyland, 2005)
            auth_match = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', block)
            year_match = re.search(r'\((\d{4})\)', block) or re.search(r'\s(\d{4})[.,]', block)
            
            if auth_match and year_match:
                soyad = auth_match.group(1)
                yil = year_match.group(1)
                
                # ÖNEMLİ: Soyadı body_text içinde ara (büyük/küçük harf duyarsız)
                # \b (word boundary) kullanarak 'Swales' ararken 'Sweller' içinde bulmasını engelle
                found_auth = re.search(rf"\b{soyad}\b", body_text, re.IGNORECASE)
                
                if not found_auth:
                    missing_in_body.append({"Eser": f"{soyad} ({yil})", "Hata": "Metinde hiç atıf yok"})
                else:
                    # Soyadı var, peki o yılla mı atıf yapılmış?
                    # Örn: Metinde Zhai (2022) var, kaynakçada Zhai (2023)
                    year_in_body = re.search(rf"{soyad}.*?(\d{{4}})", body_text, re.IGNORECASE | re.DOTALL)
                    if year_in_body:
                        metindeki_yil = year_in_body.group(1)
                        if metindeki_yil != yil:
                            wrong_year.append({
                                "Yazar": soyadı,
                                "Kaynakçadaki Yıl": yil,
                                "Metindeki Yıl": metindeki_yil,
                                "Durum": "❌ Yıl Uyuşmazlığı"
                            })

        # 3. ADIM: METİNDE VAR, KAYNAKÇADA YOK (Biggs & Tang vb.)
        missing_in_ref = []
        body_citations = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+)\s*\((\d{4})\)', body_text)
        
        for b_auth, b_year in body_citations:
            b_soyad = b_auth.strip().split()[0].replace(',', '')
            if any(word in b_soyad.lower() for word in KARA_LISTE) or len(b_soyad) < 3:
                continue
            
            is_in_ref = any(b_soyad.lower() in r_block.lower() and b_year in r_block for r_block in ref_blocks)
            if not is_in_ref:
                missing_in_ref.append({"Metindeki Atıf": f"{b_auth.strip()} ({b_year})", "Durum": "❌ Kaynakçada Yok"})

        # --- SONUÇLARI GÖSTER ---
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("🚩 Metinde Atıfı Olmayanlar")
            df_m_body = pd.DataFrame(missing_in_body).drop_duplicates()
            if not df_m_body.empty:
                st.warning(f"{len(df_m_body)} kaynak sildiğiniz için veya unutulduğu için metinde bulunamadı.")
                st.table(df_m_body)
            else:
                st.success("Tüm kaynaklar metinde kullanılmış.")

        with c2:
            st.subheader("❌ Kaynakçada Olmayanlar")
            df_m_ref = pd.DataFrame(missing_in_ref).drop_duplicates()
            if not df_m_ref.empty:
                st.error("Metinde atıf yapılmış ama kaynakça listesine eklenmemiş:")
                st.table(df_m_ref)
            else:
                st.success("Tüm atıflar kaynakçada mevcut.")

        if wrong_year:
            st.divider()
            st.subheader("📅 Yıl Yanlışları")
            st.info("Aşağıdaki yazarların metindeki yılı ile kaynakçadaki yılı birbirinden farklı.")
            st.table(pd.DataFrame(wrong_year).drop_duplicates())

    else:
        st.error("Dosyada 'References' veya 'Kaynakça' başlığı tespit edilemedi.")

import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Profesyonel Atıf Denetçisi (Kesin Çözüm)")
st.markdown("Bu sürüm, kaynakçadaki bir eseri **asla kaynakça listesinin içinde aramaz**, sadece ana metinde arar.")

def metni_temizle(text):
    # Gizli karakterleri ve satır sonu tirelemelerini (Hy- land gibi) birleştirir
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    return re.sub(r'\s+', ' ', text)

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " \n "
        doc.close()
        
        full_text = metni_temizle(full_text)

    # 1. ADIM: KAYNAKÇAYI METİNDEN AYIR (EN ÖNEMLİ KISIM)
    # References kelimesinin en SON geçtiği yeri bulur (İçindekilerle karışmaz)
    ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE))
    
    if ref_matches:
        split_point = ref_matches[-1].start()
        body_text = full_text[:split_point]  # Arama sadece burada yapılacak
        ref_text = full_text[split_point:]   # Kaynaklar buradan çekilecek
        
        # 2. ADIM: KAYNAKÇADAKİ ESERLERİ BLOKLARA AYIR
        # APA formatı: "Soyadı, A. (Yıl)" veya "Soyadı (Yıl)"
        ref_blocks = re.split(r'\n(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)|(?<=\d{4}[a-z]?\)\.)', ref_text)
        ref_blocks = [b.strip() for b in ref_blocks if len(b.strip()) > 15]

        missing_in_body = []
        year_mismatch = []

        for block in ref_blocks:
            # Soyadı ve Yılı çek
            auth_match = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', block)
            year_match = re.search(r'\((\d{4})\)', block)
            
            if auth_match and year_match:
                soyad = auth_match.group(1)
                yil = year_match.group(1)
                
                # SADECE body_text İÇİNDE ARA (\b ile tam kelime kontrolü)
                # Soyadı geçiyor mu?
                if not re.search(rf"\b{soyad}\b", body_text, re.IGNORECASE):
                    missing_in_body.append({"Eser": f"{soyad} ({yil})", "Neden": "Metinde hiç atıf yok"})
                else:
                    # Soyadı var ama yılı doğru mu? (Zhai Testi)
                    # Soyadın yanındaki 50 karakterde bu yıl var mı?
                    check_cite = rf"{soyad}.{{0,60}}{yil}"
                    if not re.search(check_cite, body_text, re.IGNORECASE | re.DOTALL):
                        # İsim var ama yıl tutmuyor. Metindeki gerçek yılı bul:
                        actual_year = re.search(rf"{soyad}.*?(\d{{4}})", body_text, re.IGNORECASE)
                        metindeki = actual_year.group(1) if actual_year else "Bulunamadı"
                        year_mismatch.append({"Yazar": soyad, "Kaynakça Yılı": yil, "Metindeki Yıl": metindeki})

        # 3. ADIM: METİNDE OLUP KAYNAKÇADA OLMAYANLAR (Biggs, Baidoo vb.)
        missing_in_ref = []
        body_cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)', body_text)
        for b_auth, b_year in body_cites:
            b_soyad = b_auth.split()[0].replace(',', '')
            if b_soyad.lower() not in ref_text.lower():
                missing_in_ref.append({"Metindeki Atıf": f"{b_auth} ({b_year})"})

        # --- GÖRSELLEŞTİRME ---
        st.divider()
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("🚩 Metinde Atıfı Olmayanlar")
            df1 = pd.DataFrame(missing_in_body).drop_duplicates()
            if not df1.empty:
                st.error("Bu eserler kaynakçada var ama metinde atıfı bulunamadı:")
                st.table(df1)
            else:
                st.success("Tüm kaynaklara atıf yapılmış.")

        with c2:
            st.subheader("❌ Kaynakçada Unutulanlar")
            df2 = pd.DataFrame(missing_in_ref).drop_duplicates()
            if not df2.empty:
                st.warning("Metinde atıfı var ama kaynakçada listelenmemiş:")
                st.table(df2)
            else:
                st.success("Eksik kaynak bulunamadı.")

        if year_mismatch:
            st.divider()
            st.subheader("📅 Yıl Uyuşmazlığı (Kritik)")
            st.info("Yazar ismi metinde geçiyor ancak yılı kaynakçadaki ile uyuşmuyor:")
            st.table(pd.DataFrame(year_mismatch).drop_duplicates())
    else:
        st.error("Kaynakça/References başlığı bulunamadı.")

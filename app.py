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
        
        full_text = re.sub(r'[ \t]+', ' ', full_text)

    # BÖLÜM AYIRMA
    split_index = -1
    ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA|REFERENCES)\b', full_text, re.IGNORECASE))
    
    if ref_matches:
        split_index = ref_matches[-1].start()

    if split_index != -1:
        body_text = full_text[:split_index]
        ref_text = full_text[split_index:]

        # KAYNAKÇAYI PARSE ET
        ref_blocks = re.split(r'\n(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)', ref_text)
        ref_blocks = [b.strip() for b in ref_blocks if len(b.strip()) > 15]

        missing_in_body = []
        year_mismatch = []

        for block in ref_blocks:
            # TÜM YAZARLARI ÇIKAR (çok yazarlı kaynaklar için)
            # Örn: "Smith, J., Jones, M., & Brown, K. (2020)" -> [Smith, Jones, Brown]
            all_authors = []
            
            # İlk yazarı yakala
            first_auth = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', block)
            if first_auth:
                all_authors.append(first_auth.group(1))
            
            # Diğer yazarları yakala (virgülden sonra gelenler)
            other_auths = re.findall(r',\s+(?:&\s+)?([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),?\s+[A-Z]\.', block)
            all_authors.extend(other_auths)
            
            # Yılı çıkar
            year_match = re.search(r'\((\d{4})\)', block)
            
            if all_authors and year_match:
                yil = year_match.group(1)
                birinci_yazar = all_authors[0]
                
                # KRİTİK DEĞİŞİKLİK: Herhangi bir yazarın geçip geçmediğini kontrol et
                found_any_author = False
                for soyad in all_authors:
                    pattern = rf"\b{soyad}\b"
                    if re.search(pattern, body_text, re.IGNORECASE):
                        found_any_author = True
                        break
                
                # Et al. kontrolü de ekle
                if not found_any_author:
                    # "İlk yazar et al." formatını kontrol et
                    et_al_pattern = rf"\b{birinci_yazar}\s+et\s+al\.?"
                    if re.search(et_al_pattern, body_text, re.IGNORECASE):
                        found_any_author = True
                
                if not found_any_author:
                    # HİÇBİR YAZAR METINDE YOK
                    authors_display = ", ".join(all_authors[:3])
                    if len(all_authors) > 3:
                        authors_display += " et al."
                    missing_in_body.append({"Kaynakçadaki Eser": f"{authors_display} ({yil})"})
                else:
                    # En az bir yazar var, şimdi yıl kontrolü
                    year_found = False
                    for soyad in all_authors:
                        year_pattern = rf"{soyad}.*?{yil}|{yil}.*?{soyad}"
                        if re.search(year_pattern, body_text, re.IGNORECASE | re.DOTALL):
                            year_found = True
                            break
                    
                    # Et al. ile yıl kontrolü
                    if not year_found:
                        et_al_year = rf"{birinci_yazar}\s+et\s+al\.?.*?{yil}|{yil}.*?{birinci_yazar}\s+et\s+al\.?"
                        if re.search(et_al_year, body_text, re.IGNORECASE | re.DOTALL):
                            year_found = True
                    
                    if not year_found:
                        # Yazar var ama yıl yanlış
                        actual_year_match = re.search(rf"{birinci_yazar}.*?(\d{{4}})", body_text, re.IGNORECASE | re.DOTALL)
                        metin_yili = actual_year_match.group(1) if actual_year_match else "Bulunamadı"
                        year_mismatch.append({
                            "Yazar": birinci_yazar,
                            "Kaynakçada": yil,
                            "Metinde": metin_yili
                        })

        # METİNDE VAR KAYNAKÇADA YOK
        missing_in_ref = []
        
        # Tek yazar: Author (2020) veya (Author, 2020)
        single_cits = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s*\((\d{4})\)', body_text)
        
        # Çift yazar: Author & Author (2020) veya Author and Author (2020)
        double_cits = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+(?:&|and)\s+([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s*\((\d{4})\)', body_text)
        
        # Et al: Author et al. (2020)
        et_al_cits = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+et\s+al\.?\s*\((\d{4})\)', body_text)
        
        # Tek yazar kontrolü
        for b_auth, b_year in single_cits:
            if any(k in b_auth.lower() for k in KARA_LISTE): continue
            
            is_in_ref = any(b_auth.lower() in r_block.lower() and b_year in r_block for r_block in ref_blocks)
            if not is_in_ref:
                if {"Metindeki Atıf": f"{b_auth} ({b_year})"} not in missing_in_ref:
                    missing_in_ref.append({"Metindeki Atıf": f"{b_auth} ({b_year})"})
        
        # Çift yazar kontrolü
        for auth1, auth2, b_year in double_cits:
            if any(k in auth1.lower() for k in KARA_LISTE): continue
            
            is_in_ref = any((auth1.lower() in r_block.lower() and auth2.lower() in r_block.lower() and b_year in r_block) for r_block in ref_blocks)
            if not is_in_ref:
                citation_str = f"{auth1} & {auth2} ({b_year})"
                if {"Metindeki Atıf": citation_str} not in missing_in_ref:
                    missing_in_ref.append({"Metindeki Atıf": citation_str})
        
        # Et al kontrolü
        for b_auth, b_year in et_al_cits:
            if any(k in b_auth.lower() for k in KARA_LISTE): continue
            
            is_in_ref = any(b_auth.lower() in r_block.lower() and b_year in r_block for r_block in ref_blocks)
            if not is_in_ref:
                citation_str = f"{b_auth} et al. ({b_year})"
                if {"Metindeki Atıf": citation_str} not in missing_in_ref:
                    missing_in_ref.append({"Metindeki Atıf": citation_str})

        # EKRAN ÇIKTILARI
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

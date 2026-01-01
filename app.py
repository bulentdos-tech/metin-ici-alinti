import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Profesyonel Atıf Denetçisi")
st.markdown("Metin ve Kaynakça arasındaki tutarsızlıkları raporlar.")

# Analiz dışı bırakılacak kelimeler
KARA_LISTE = ["march", "april", "university", "journal", "retrieved", "from", "doi", "http", "https", "pdf", "page", "january"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Dosya derinlemesine analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " \n "
        doc.close()
        
        # Fazla boşlukları temizle ama satır yapısını koru
        clean_text = re.sub(r'[ \t]+', ' ', full_text)

    # 1. KAYNAKÇA AYIRMA (En kritik nokta)
    # Sadece sayfanın başında veya tek başına duran "References" başlığını bulmaya çalışır
    ref_patterns = [r'\nReferences\s*\n', r'\nKaynakça\s*\n', r'\nKAYNAKÇA\s*\n']
    split_index = -1
    for pattern in ref_patterns:
        matches = list(re.finditer(pattern, clean_text, re.IGNORECASE))
        if matches:
            split_index = matches[-1].start()
            break
    
    # Eğer özel başlık kalıbı bulunamazsa klasik yönteme dön
    if split_index == -1:
        for kw in ["References", "Kaynakça", "KAYNAKÇA"]:
            idx = clean_text.rfind(kw)
            if idx > len(clean_text) * 0.5: # Sayfanın en az yarısından sonra olmalı
                split_index = idx
                break

    if split_index != -1:
        body_text = clean_text[:split_index]
        # Kaynakçanın kendisi arama dışında kalsın diye sadece üst kısmı body_text yaptık.
        
        raw_ref_section = clean_text[split_index:]
        
        # Kaynakça bloklarını daha hassas böl (Soyadı, A. (Yıl) formatı için)
        ref_blocks = [b.strip() for b in re.split(r'\n(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)', raw_ref_section) if len(b.strip()) > 15]

        # --- ANALİZ 1: METİNDE VAR, KAYNAKÇADA YOK ---
        text_citations = []
        # (Yazar, 2020) veya Yazar (2020) kalıpları
        matches = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+)\s*\((\d{4}[a-z]?)\)', body_text)
        for auth, yr in matches:
            auth_clean = auth.replace('&', '').strip()
            if not any(word in auth_clean.lower() for word in KARA_LISTE) and len(auth_clean) > 2:
                text_citations.append({"auth": auth_clean.split()[0], "year": yr, "full": f"{auth.strip()} ({yr})"})

        missing_in_ref = []
        for cit in text_citations:
            # Kaynakça bloğunda yazar soyadı ve yıl yan yana mı?
            found = any(cit["auth"].lower() in block.lower() and cit["year"] in block for block in ref_blocks)
            if not found:
                missing_in_ref.append({"Metindeki Atıf": cit["full"], "Hata": "❌ Kaynakçada Yok"})

        df_missing_in_ref = pd.DataFrame(missing_in_ref).drop_duplicates()

        # --- ANALİZ 2: KAYNAKÇADA VAR, METİNDE YOK ---
        unused_refs = []
        for block in ref_blocks:
            # Bloktan ilk kelimeyi (Soyad) ve yılı çek
            first_word = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', block)
            year_match = re.search(r'(\d{4})', block)
            
            if first_word and year_match:
                soyad = first_word.group(1)
                yil = year_match.group(1)
                
                # Metin içinde (Soyad, Yıl) veya Soyad (Yıl) olarak geçiyor mu?
                # \b ile tam kelime kontrolü yapıyoruz ki "Sweller" içindeki "Swales"ı bulmasın.
                pattern = rf"\b{soyad}\b.*?{yil}|{yil}.*?\b{soyad}\b"
                is_cited = re.search(pattern, body_text, re.IGNORECASE | re.DOTALL)
                
                if not is_cited:
                    unused_refs.append({"Kaynakçadaki Eser": block[:120] + "...", "Hata": "⚠️ Metinde Atıfı Yok"})

        df_unused_refs = pd.DataFrame(unused_refs)

        # --- EKRAN ÇIKTISI ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("❌ Kaynakçada Bulunmayanlar")
            if not df_missing_in_ref.empty:
                st.table(df_missing_in_ref)
            else:
                st.success("Tebrikler! Metindeki tüm atıflar kaynakçada mevcut.")

        with col2:
            st.subheader("⚠️ Metinde Atıfı Olmayanlar")
            if not df_unused_refs.empty:
                st.table(df_unused_refs)
            else:
                st.success("Tebrikler! Kaynakçadaki tüm eserlere metin içinde atıf yapılmış.")

        # Excel Raporu
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_missing_in_ref.to_excel(writer, sheet_name='Eksik Kaynaklar', index=False)
            df_unused_refs.to_excel(writer, sheet_name='Atıfı Olmayanlar', index=False)
        st.divider()
        st.download_button("📥 Hata Raporunu İndir", output.getvalue(), "denetim_raporu.xlsx")
    else:
        st.error("Kaynakça/References başlığı bulunamadı. Lütfen dosyanın formatını kontrol edin.")

import streamlit as st
import pandas as pd
import re
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Akıllı Atıf & Kaynakça Denetçisi")
st.markdown("Metin içi atıfları soyadı ve yıl bazında kaynakça ile eşleştirir.")

uploaded_file = st.file_uploader("Analiz edilecek PDF'i yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Dosya okunuyor ve temizleniyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            # Metni alırken satır sonu tirelerini birleştir
            text = page.get_text("text")
            text = re.sub(r'-\s*\n', '', text) # Satır sonu tireleme (Örn: 1041- 6080)
            full_text += text + " "
        doc.close()
        
        # Fazla boşlukları temizle
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakçayı Ayır
    ref_keywords = [r'\bKaynakça\b', r'\bReferences\b', r'\bKAYNAKÇA\b', r'\bREFERENCES\b']
    split_index = -1
    for kw in ref_keywords:
        matches = list(re.finditer(kw, full_text))
        if matches:
            split_index = matches[-1].start()
            break

    if split_index != -1:
        body_text = full_text[:split_index]
        references_text = full_text[split_index:]

        # 2. Atıfları Yakala
        # (Yazar, 2021) veya Yazar (2021) veya Yazar et al. (2023)
        patterns = [
            r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)', # Metin içi
            r'\(([^)]+),\s*(\d{4})\)' # Parantez içi
        ]
        
        citations = []
        for p in patterns:
            for m in re.finditer(p, body_text):
                raw_yazar = m.group(1)
                yil = m.group(2)
                
                # Soyadlarını temizle (Bembenutty & Karabenick -> ['Bembenutty', 'Karabenick'])
                # Sadece büyük harfle başlayan kelimeleri soyadı kabul et
                soyadi_listesi = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', raw_yazar)
                
                citations.append({
                    "tam_atif": f"{raw_yazar} ({yil})",
                    "soyadlar": soyadi_listesi,
                    "yil": yil
                })

        df_raw = pd.DataFrame(citations).drop_duplicates(subset=['tam_atif'])

        # 3. Akıllı Karşılaştırma
        results = []
        ref_lower = references_text.lower()

        for _, row in df_raw.iterrows():
            found = False
            # Eğer soyadlarından en az biri ve yıl kaynakçada aynı yerlerdeyse true dön
            # Daha garanti olması için ilk soyadı mutlaka kontrol et
            if row['soyadlar']:
                ana_soyad = row['soyadlar'][0].lower()
                yil = row['yil']
                
                # Kaynakçada hem soyadı hem yıl geçiyor mu?
                if ana_soyad in ref_lower and yil in ref_lower:
                    found = True
            
            results.append({
                "Atıf": row['tam_atif'],
                "Durum": "✅ Kaynakçada Var" if found else "❌ Kaynakçada Yok",
                "Aranan Soyadı": row['soyadlar'][0] if row['soyadlar'] else "Bulunamadı"
            })

        # 4. Arayüz
        df_res = pd.DataFrame(results)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Atıf Listesi")
            st.dataframe(df_res, use_container_width=True)
            
        with col2:
            st.subheader("Hata Özeti")
            errors = df_res[df_res['Durum'] == "❌ Kaynakçada Yok"]
            if not errors.empty:
                st.error(f"{len(errors)} Atıf bulunamadı!")
                st.write(errors['Atıf'].unique())
            else:
                st.success("Tüm atıflar doğrulandı!")

    else:
        st.warning("Kaynakça başlığı bulunamadı.")

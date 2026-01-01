import streamlit as st
import pandas as pd
import re
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Gelişmiş Atıf & Kaynakça Denetçisi")
st.markdown("Bogoch et al. gibi satır arası kırılmaları ve çoklu atıfları destekleyen güncel sürüm.")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Metin derinlemesine analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            # Sayfadaki metni al
            text = page.get_text("text")
            # 1. Önce satır sonu tirelerini birleştir
            text = re.sub(r'-\s*\n', '', text)
            # 2. Satır sonu karakterlerini boşluğa çevir (Bogoch \n et al. durumunu çözer)
            text = text.replace('\n', ' ')
            full_text += text + " "
        doc.close()
        
        # Fazla boşlukları temizle ve tek satır haline getir
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakça Bölümünü Ayır
    ref_keywords = [r'\bKaynakça\b', r'\bReferences\b', r'\bKAYNAKÇA\b', r'\bREFERENCES\b']
    split_index = -1
    for kw in ref_keywords:
        matches = list(re.finditer(kw, full_text, re.IGNORECASE))
        if matches:
            split_index = matches[-1].start()
            break

    if split_index != -1:
        body_text = full_text[:split_index]
        ref_text = full_text[split_index:].lower()

        # 2. Atıfları Yakala (Noktalı virgülle ayrılmış grupları destekler)
        # Önce parantez içindeki tüm bloğu yakala: (Rodríguez-Morales et al., 2020; Bogoch et al., 2020)
        paren_groups = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        
        # Parantez dışındaki metin içi atıflar: Mayer (2021)
        inline_citations = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)

        results = []

        # Parantez gruplarını parçala (Bogoch'u burada yakalayacağız)
        for group in paren_groups:
            # Noktalı virgüle göre böl
            sub_citations = group.split(';')
            for sub in sub_citations:
                year_match = re.search(r'\d{4}', sub)
                if year_match:
                    year = year_match.group()
                    # Soyadlarını/Kurumları bul
                    authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+|[A-ZÇĞİÖŞÜ]{2,}', sub)
                    if authors:
                        # Kaynakçada kontrol
                        found = any(a.lower() in ref_text for a in authors) and year in ref_text
                        results.append({
                            "Atıf": sub.strip(),
                            "Eşleşen Yazarlar": ", ".join(authors),
                            "Yıl": year,
                            "Durum": "✅ Kaynakçada Var" if found else "❌ Kaynakçada Yok"
                        })

        # Metin içi atıfları ekle
        for auth, yr in inline_citations:
            found = auth.split()[0].lower() in ref_text and yr in ref_text
            results.append({
                "Atıf": f"{auth} ({yr})",
                "Eşleşen Yazarlar": auth,
                "Yıl": yr,
                "Durum": "✅ Kaynakçada Var" if found else "❌ Kaynakçada Yok"
            })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Atıf'])

        # 3. Arayüz ve Excel
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("Tespit Edilen Atıflar")
            st.dataframe(df_res, use_container_width=True)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_res.to_excel(writer, index=False)
            
            st.download_button("📊 Raporu Excel Olarak İndir", output.getvalue(), "denetim_raporu.xlsx")
            
        with col2:
            st.metric("Toplam Atıf", len(df_res))
            st.metric("Eksik Sayısı", len(df_res[df_res['Durum'] == "❌ Kaynakçada Yok"]))

    else:
        st.error("Kaynakça tespit edilemedi.")

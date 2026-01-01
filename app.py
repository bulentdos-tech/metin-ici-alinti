import streamlit as st
import pandas as pd
import re
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Akademik Denetçi v2", layout="wide")

st.title("🔍 Akıllı Atıf & Kaynakça Karşılaştırıcı")

uploaded_file = st.file_uploader("PDF Dosyasını Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Dosya derinlemesine analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text").replace('-\n', '').replace('\n', ' ') + " "
        doc.close()

    # 1. KAYNAKÇAYI TESPİT ET (Daha esnek bir arama)
    ref_patterns = [r'\bKaynakça\b', r'\bReferences\b', r'\bBibliyografya\b', r'\bWORKS CITED\b']
    split_index = -1
    for pattern in ref_patterns:
        match = list(re.finditer(pattern, full_text, re.IGNORECASE))
        if match:
            # Genelde kaynakça sondadır, o yüzden son eşleşmeyi alalım
            split_index = match[-1].start()
            break

    if split_index != -1:
        body_text = full_text[:split_index]
        references_text = full_text[split_index:]

        # Görsel Kontrol İçin Kaynakça Başlangıcını Göster
        with st.expander("📌 Algılanan Kaynakça Bölümü (İlk 500 Karakter)"):
            st.write(references_text[:500] + "...")

        # 2. METİN İÇİ ALINTILARI BUL
        # Desen 1: (Yazar, 2020) veya (Yazar1 & Yazar2, 2020)
        pattern1 = r'\(([^)]+),\s(\d{4}[a-z]?)\)'
        # Desen 2: Yazar (2020) veya Yazar et al. (2020)
        pattern2 = r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\set\sal\.)?)\s\((\d{4}[a-z]?)\)'

        found_citations = []
        
        for m in re.finditer(pattern1, body_text):
            found_citations.append({"yazar": m.group(1), "yil": m.group(2)})
        for m in re.finditer(pattern2, body_text):
            found_citations.append({"yazar": m.group(1), "yil": m.group(2)})

        df_raw = pd.DataFrame(found_citations).drop_duplicates()

        # 3. KARŞILAŞTIRMA MANTIĞI
        analysis_results = []
        ref_text_lower = references_text.lower()

        for _, row in df_raw.iterrows():
            yazar_ham = row['yazar'].lower()
            # Soyadını çek: "Smith et al." -> "smith", "Smith & Doe" -> "smith"
            soyad = re.split(r'[,&\s]|et\sal', yazar_ham)[0].strip()
            yil = row['yil']

            # Kaynakçada hem soyadı hem yıl aynı anda geçiyor mu?
            # (Aynı cümle/alan içinde olma şartı aranabilir ama şimdilik metin geneli)
            if soyad in ref_text_lower and yil in ref_text_lower:
                durum = "✅ Kaynakçada Mevcut"
            else:
                durum = "❌ KAYNAKÇADA BULUNAMADI"

            analysis_results.append({
                "Metindeki Alıntı": f"{row['yazar']} ({yil})",
                "Aranan Soyad": soyad,
                "Yıl": yil,
                "Durum": durum
            })

        df_final = pd.DataFrame(analysis_results)

        # 4. SONUÇLARI GÖSTER
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📊 Tüm Atıflar")
            def color_rows(val):
                color = '#ffcccc' if val == "❌ KAYNAKÇADA BULUNAMADI" else '#ccffcc'
                return f'background-color: {color}'
            
            st.dataframe(df_final.style.applymap(color_rows, subset=['Durum']), use_container_width=True)

        with col2:
            st.subheader("🚨 Eksik Kaynaklar")
            eksikler = df_final[df_final['Durum'] == "❌ KAYNAKÇADA BULUNAMADI"]
            if not eksikler.empty:
                st.error(f"{len(eksikler)} kaynak listede yok!")
                for e in eksikler['Metindeki Alıntı'].unique():
                    st.write(f"- {e}")
            else:
                st.success("Tüm atıflar kaynakça ile eşleşiyor!")

    else:
        st.error("⚠️ Kaynakça bölümü tespit edilemedi! PDF'de 'Kaynakça' veya 'References' başlığı olduğundan emin olun.")

st.divider()
st.caption("Bülent Dos | Gelişmiş Akademik Denetim Sistemi")

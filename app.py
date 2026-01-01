import streamlit as st
import pandas as pd
import re
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Akademik Denetçi", layout="wide")

st.title("🔍 Akademik Atıf & Kaynakça Denetçisi")
st.markdown("PDF'deki metin içi alıntıları ve kaynakçayı karşılaştırarak eksikleri tespit eder.")

uploaded_file = st.file_uploader("Bir PDF Dosyası Yükleyin", type="pdf")

if uploaded_file:
    all_text = ""
    with st.spinner('Dosya analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page in doc:
            all_text += page.get_text("text").replace('-\n', '').replace('\n', ' ') + " "
        doc.close()

    # 1. Metni ve Kaynakçayı Ayır
    ref_keywords = [r'\bKaynakça\b', r'\bReferences\b', r'\bKAYNAKÇA\b', r'\bREFERENCES\b']
    split_index = -1
    for kw in ref_keywords:
        match = re.search(kw, all_text)
        if match:
            split_index = match.start()
            break

    if split_index != -1:
        body_text = all_text[:split_index]
        references_text = all_text[split_index:]
        
        # 2. Metin İçi Alıntıları Bul (Yazar ve Yıl)
        # Örn: (Smith, 2020) veya Smith (2020)
        citation_pattern = r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)?(?: et al\.)?)[^()]*\((\d{4})\)'
        paren_pattern = r'\(([A-ZÇĞİÖŞÜ][a-zçğıöşü\s,]+),\s(\d{4})\)'
        
        found_citations = []
        
        # Parantez dışındakiler
        for match in re.finditer(citation_pattern, body_text):
            found_citations.append({"yazar": match.group(1), "yil": match.group(2), "tip": "Metin İçi"})
            
        # Parantez içindekiler
        for match in re.finditer(paren_pattern, body_text):
            found_citations.append({"yazar": match.group(1), "yil": match.group(2), "tip": "Parantez İçi"})

        df_citations = pd.DataFrame(found_citations).drop_duplicates()

        # 3. Karşılaştırma Yap
        results = []
        for _, row in df_citations.iterrows():
            # Kaynakça içinde yazar ve yıl geçiyor mu?
            # Basit kontrol: Yazar ismi ve Yıl aynı "paragraf" veya yakınlıkta mı?
            yazar_soyad = row['yazar'].split()[-1] if ' ' in row['yazar'] else row['yazar']
            match_in_ref = re.search(f"{yazar_soyad}.*{row['yil']}", references_text, re.IGNORECASE)
            
            status = "✅ Kaynakçada Var" if match_in_ref else "❌ KAYNAKÇADA EKSİK!"
            results.append({
                "Alıntı": f"{row['yazar']} ({row['yil']})",
                "Tür": row['tip'],
                "Durum": status
            })

        df_results = pd.DataFrame(results)

        # 4. Arayüz Gösterimi
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Atıf Analizi")
            st.dataframe(df_results, use_container_width=True)

        with col2:
            st.subheader("📝 Tespit Edilen Eksikler")
            eksikler = df_results[df_results['Durum'] == "❌ KAYNAKÇADA EKSİK!"]
            if not eksikler.empty:
                st.error(f"{len(eksikler)} adet eksik kaynak tespit edildi!")
                st.table(eksikler[['Alıntı']])
            else:
                st.success("Harika! Tüm metin içi atıflar kaynakçada bulunuyor.")

        # Excel İndirme
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_results.to_excel(writer, index=False)
        
        st.download_button(
            label="Raporu Excel Olarak İndir",
            data=output.getvalue(),
            file_name="atik_kontrol_raporu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("PDF içinde 'Kaynakça' veya 'References' başlığı bulunamadı. Lütfen dosyanızı kontrol edin.")

st.divider()
st.caption("Geliştirici: Bülent Dos | Akademik Denetim Araçları")

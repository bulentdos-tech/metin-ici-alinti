import streamlit as st
import pandas as pd
import re
import fitz  # PyMuPDF
import io

# Sayfa Ayarları
st.set_page_config(page_title="Akademik Alıntı Ayıklayıcı", layout="wide")

st.title("📄 Akademik PDF Alıntı Ayıklayıcı")
st.markdown("PDF dosyalarınızı yükleyin, metin içi alıntıları (APA) otomatik olarak Excel'e aktaralım.")

uploaded_files = st.file_uploader("PDF Dosyalarını Seçin", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_data = []
    
    with st.spinner('Dosyalar analiz ediliyor...'):
        for uploaded_file in uploaded_files:
            try:
                # PDF'i oku
                file_content = uploaded_file.read()
                doc = fitz.open(stream=file_content, filetype="pdf")
                
                full_text = ""
                for page in doc:
                    text = page.get_text("text")
                    # Satır sonu ve boşluk temizliği
                    text = text.replace('-\n', '').replace('\n', ' ')
                    full_text += text + " "
                
                full_text = re.sub(r'\s+', ' ', full_text)
                
                # Kaynakçayı kes
                ref_keywords = ['Kaynakça', 'References', 'KAYNAKÇA', 'REFERENCES']
                for kw in ref_keywords:
                    if kw in full_text:
                        full_text = full_text.split(kw)[0]
                        break
                
                # Güçlendirilmiş APA Desenleri
                patterns = {
                    'Parantez İçi (APA)': r'\([A-ZÇĞİÖŞÜ][^)]+\d{4}[^)]*\)',
                    'Metin İçi (Anlatı)': r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,}[^()]{0,50}\(\d{4}\)'
                }
                
                for style, pattern in patterns.items():
                    found = re.findall(pattern, full_text)
                    for item in found:
                        item_clean = re.sub(r'\s+', ' ', item).strip()
                        
                        # Filtreleme
                        if style == 'Metin İçi (Anlatı)' and (len(item_clean) > 80 or len(item_clean) < 5):
                            continue
                        
                        # Yıl ve Yazar Ayıklama
                        yil_match = re.search(r'\d{4}', item_clean)
                        yil = yil_match.group() if yil_match else ""
                        yazar = item_clean.split('(')[0].strip() if '(' in item_clean else item_clean
                        yazar = yazar.strip('() ,;')

                        all_data.append({
                            "Dosya Adı": uploaded_file.name,
                            "Yazar/Grup": yazar,
                            "Yıl": yil,
                            "Stil": style,
                            "Tam Alıntı": item_clean
                        })
                doc.close()
            except Exception as e:
                st.error(f"Hata: {uploaded_file.name} - {str(e)}")

    if all_data:
        df = pd.DataFrame(all_data).drop_duplicates()
        st.success(f"İşlem Tamam! {len(df)} alıntı listelendi.")
        st.dataframe(df, use_container_width=True)
        
        # Excel İndirme
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output) as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📊 Excel Dosyasını İndir",
                data=output.getvalue(),
                file_name="alintilar.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as excel_hata:
            st.error(f"Excel hatası: {excel_hata}")
    else:
        st.info("Alıntı bulunamadı.")

st.divider()
st.caption("Geliştirici: Bülent Dos | Akademik Araştırma Araçları")

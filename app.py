import streamlit as st
import pandas as pd
import re
import fitz  # PyMuPDF
import io

# Sayfa Ayarları
st.set_page_config(page_title="Akademik Alıntı Ayıklayıcı", layout="wide")

st.title("📄 Akademik PDF Alıntı Ayıklayıcı (Profesyonel)")
st.markdown("""
Bu araç, PDF dosyalarınızdaki metin içi alıntıları (APA stili) tespit eder ve Excel'e aktarır. 
**Yenilik:** Çoklu yazarlar, '&' işareti ve satır sonu kaymaları artık destekleniyor.
""")

uploaded_files = st.file_uploader("PDF Dosyalarını Seçin", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_data = []
    
    with st.spinner('Dosyalar analiz ediliyor, lütfen bekleyin...'):
        for uploaded_file in uploaded_files:
            try:
                # PDF'i oku
                file_content = uploaded_file.read()
                doc = fitz.open(stream=file_content, filetype="pdf")
                
                full_text = ""
                for page in doc:
                    text = page.get_text("text")
                    # Satır sonu tirelerini ve gereksiz boşlukları temizle
                    text = text.replace('-\n', '').replace('\n', ' ')
                    full_text += text + " "
                
                # Gereksiz çift boşlukları temizle
                full_text = re.sub(r'\s+', ' ', full_text)
                
                # Kaynakçayı kes
                ref_keywords = ['Kaynakça', 'References', 'KAYNAKÇA', 'REFERENCES', 'Works Cited']
                for kw in ref_keywords:
                    if kw in full_text:
                        full_text = full_text.split(kw)[0]
                        break
                
                # GÜÇLENDİRİLMİŞ APA DESENLERİ
                patterns = {
                    'APA_Parenthetical': r'\([A-ZÇĞİÖŞÜ][^)]+\d{4}[^)]*\)',
                    'APA_Narrative': r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,}[^()]{0,50}\(\d{4}\)'
                }
                
                for style, pattern in patterns.items():
                    found = re.findall(pattern, full_text)
                    
                    for item in found:
                        item_clean = re.sub(r'\s+', ' ', item).strip()
                        
                        if style == 'APA_Narrative' and (len(item_clean) > 80 or len(item_clean) < 5):
                            continue
                        
                        yil_match = re.search(r'\d{4}', item_clean)
                        yil = yil_match.group() if yil_match else ""
                        
                        yazar = item_clean.split('(')[0].strip() if '(' in item_clean else item_clean
                        yazar = yazar.strip('() ,;')

                        all_data.append({
                            "Dosya Adı": uploaded_file.name,
                            "Yazar/Grup": yazar,
                            "Yıl": yil,
                            "Alıntı Tipi": style,
                            "Tam Metin": item_clean
                        })
                doc.close()
            except Exception as e:
                st.error(f"{uploaded_file.name} işlenirken bir hata oluştu: {e}")

    if all_data:
        df = pd.DataFrame(all_data)
        df = df.drop_duplicates()
        
        st.success(f"İşlem Tamamlandı! Toplam {len(df)} benzersiz alıntı bulundu.")
        st.dataframe(df, use_container_width=True)
        
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output) as writer:
                df.to_

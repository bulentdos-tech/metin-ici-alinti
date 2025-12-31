import streamlit as st
import pandas as pd
import re
import fitz  # PyMuPDF
from utils.extractor import CitationExtractor
import io

st.set_page_config(page_title="Akademik Alıntı Ayıklayıcı", layout="wide")

st.title("📄 Akademik PDF Alıntı Ayıklayıcı")
st.markdown("PDF dosyalarınızı yükleyin, metin içi alıntıları (APA) otomatik olarak Excel'e dönüştürelim.")

uploaded_files = st.file_uploader("PDF Dosyalarını Seçin", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_data = []
    
    with st.spinner('Dosyalar işleniyor...'):
        for uploaded_file in uploaded_files:
            # Geçici olarak dosyayı oku
            file_content = uploaded_file.read()
            doc = fitz.open(stream=file_content, filetype="pdf")
            
            # Mevcut extractor mantığını buraya entegre ediyoruz
            # (Basitlik için extractor'ı burada doğrudan çağırıyoruz)
            full_text = ""
            for page in doc:
                text = page.get_text("text")
                text = text.replace('-\n', '').replace('\n', ' ')
                full_text += text + " "
            full_text = re.sub(r'\s+', ' ', full_text)
            
            # Kaynakçayı kes
            ref_keywords = ['Kaynakça', 'References', 'KAYNAKÇA', 'REFERENCES']
            for kw in ref_keywords:
                if kw in full_text:
                    full_text = full_text.split(kw)[0]
                    break
            
            patterns = {
                'APA_Parenthetical': r'\([A-ZÇĞİÖŞÜ][a-zçğıöşü\s\w\.\&\-üÜİıĞğŞşÇçÖö]+,\s\d{4}(?::\s\d+)?\)',
                'APA_Narrative': r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,}[a-zçğıöşü\s\w\.\-üÜİıĞğŞşÇçÖö]{0,30}\s\(\d{4}\)'
            }
            
            for style, pattern in patterns.items():
                found = re.findall(pattern, full_text)
                cleaned = sorted(list(set([re.sub(r'\s+', ' ', f).strip() for f in found])))
                
                for item in cleaned:
                    # Filtreleme
                    if style == 'APA_Narrative' and (len(item) > 60 or len(item.split(' (')[0]) < 3):
                        continue
                        
                    yil_bul = re.search(r'\d{4}', item)
                    yil = yil_bul.group() if yil_bul else ""
                    yazar = item.replace(yil, "").replace("()", "").replace("(, )", "").strip(" (.,:)")
                    
                    all_data.append({
                        "Dosya Adı": uploaded_file.name,
                        "Yazar": yazar,
                        "Yıl": yil,
                        "Stil": style,
                        "Tam Alıntı": item
                    })

    if all_data:
        df = pd.DataFrame(all_data)
        st.success(f"İşlem tamam! Toplam {len(df)} alıntı bulundu.")
        
        # Önizleme
        st.dataframe(df, use_container_width=True)
        
        # Excel İndirme Butonu
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📊 Sonuçları Excel Olarak İndir",
            data=output.getvalue(),
            file_name="alıntı_listesi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Seçilen dosyalarda alıntı bulunamadı.")


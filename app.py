import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Stabil", layout="wide")

st.title("🔍 Atıf Denetçisi (Stabil Sürüm)")
st.info("Bu sürüm sadece metin içinde atıf yapılıp KAYNAKÇADA UNUTULAN eserleri listeler.")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " "
        doc.close()

        # Metni temizle ve tek bir satır haline getir (Gizli karakterleri yok et)
        full_text = re.sub(r'\s+', ' ', full_text)

        # 1. ADIM: KAYNAKÇA BÖLÜMÜNÜ TESPİT ET
        # En sondaki References/Kaynakça başlığını bulur
        ref_header = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE))
        
        if ref_header:
            split_idx = ref_header[-1].start()
            body_text = full_text[:split_idx]
            ref_section = full_text[split_idx:]
            
            # 2. ADIM: METİN İÇİNDEKİ ATIFLARI BUL
            # (Yazar, 2020) veya Yazar (2020) kalıpları
            # Bu regex Biggs & Tang gibi yapıları da yakalar
            cites_in_body = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+)\s*\((\d{4}[a-z]?)\)', body_text)
            
            results = []
            
            # 3. ADIM: KONTROL (Sadece metinde olup kaynakçada olmayana bakıyoruz)
            for author, year in cites_in_body:
                # Temizlik: İlk yazarın soyadını al
                clean_author = author.replace(" et al.", "").replace("&", " ").split()[0].strip()
                
                # Tablo ve Şekil atıflarını ele
                if clean_author.lower() in ["table", "figure", "appendix", "chatgpt", "ai"]:
                    continue
                
                # Kaynakça bloğunda bu soyadı ve yılı ara
                # Regex ile esnek arama: İsim ve yıl arasında herhangi bir karakter olabilir
                found = re.search(rf"{clean_author}.*?{year}", ref_section, re.IGNORECASE)
                
                if not found:
                    results.append({
                        "Metindeki Atıf": f"{author.strip()} ({year})",
                        "Hata Türü": "❌ Kaynakçada Yok"
                    })

            # SONUÇLARI GÖSTER
            if results:
                df = pd.DataFrame(results).drop_duplicates()
                st.error(f"⚠️ Toplam {len(df)} kaynak eksik:")
                st.table(df)
            else:
                st.success("✅ Metindeki tüm atıflar kaynakçada bulundu.")
        else:
            st.warning("Dosyada 'References' veya 'Kaynakça' başlığı bulunamadı.")

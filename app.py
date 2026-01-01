import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Stabil", layout="wide")
st.title("🔍 Atıf Denetçisi (İyileştirilmiş Sürüm)")
st.info("Bu sürüm sadece metin içinde atıf yapılıp KAYNAKÇADA UNUTULAN eserleri listeler.")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " "
        doc.close()
        
        # Metni temizle
        full_text = re.sub(r'\s+', ' ', full_text)
        
        # KAYNAKÇA BÖLÜMÜNÜ TESPİT ET
        ref_header = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA|REFERENCES)\b', full_text, re.IGNORECASE))
        
        if ref_header:
            split_idx = ref_header[-1].start()
            body_text = full_text[:split_idx]
            ref_section = full_text[split_idx:]
            
            # METİN İÇİNDEKİ ATIFLARI BUL
            results = []
            
            # 1. TEK YAZAR: Author (2020) veya (Author, 2020)
            single_cites = re.findall(r'\b([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s*\((\d{4}[a-z]?)\)', body_text)
            
            # 2. ÇİFT YAZAR: Author & Author (2020) veya Author and Author (2020)
            double_cites = re.findall(r'\b([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+(?:&|and)\s+([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s*\((\d{4}[a-z]?)\)', body_text)
            
            # 3. ÇOK YAZAR (ET AL.): Author et al. (2020)
            etal_cites = re.findall(r'\b([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+et\s+al\.?\s*\((\d{4}[a-z]?)\)', body_text, re.IGNORECASE)
            
            # KARA LİSTE (Hatalı atıf tespitlerini önle)
            blacklist = ["table", "figure", "appendix", "chatgpt", "ai", "university", "page", "vol", "journal"]
            
            # TEK YAZAR KONTROLÜ
            for author, year in single_cites:
                if author.lower() in blacklist:
                    continue
                
                # Kaynakçada hem yazar hem yıl var mı?
                # Yıldaki harf varsa (2020a) harf olmadan da ara
                year_base = re.sub(r'[a-z]$', '', year)
                
                # Esnek arama: Yazar ve yıl aynı satırda olmalı
                pattern = rf'\b{author}\b.*?\({year_base}[a-z]?\)'
                found = re.search(pattern, ref_section, re.IGNORECASE | re.DOTALL)
                
                if not found:
                    results.append({
                        "Metindeki Atıf": f"{author} ({year})",
                        "Hata Türü": "❌ Kaynakçada Yok"
                    })
            
            # ÇİFT YAZAR KONTROLÜ
            for auth1, auth2, year in double_cites:
                if auth1.lower() in blacklist or auth2.lower() in blacklist:
                    continue
                
                year_base = re.sub(r'[a-z]$', '', year)
                
                # Her iki yazar da kaynakçada olmalı
                pattern = rf'\b{auth1}\b.*?\b{auth2}\b.*?\({year_base}[a-z]?\)|\b{auth2}\b.*?\b{auth1}\b.*?\({year_base}[a-z]?\)'
                found = re.search(pattern, ref_section, re.IGNORECASE | re.DOTALL)
                
                if not found:
                    results.append({
                        "Metindeki Atıf": f"{auth1} & {auth2} ({year})",
                        "Hata Türü": "❌ Kaynakçada Yok"
                    })
            
            # ET AL. KONTROLÜ
            for author, year in etal_cites:
                if author.lower() in blacklist:
                    continue
                
                year_base = re.sub(r'[a-z]$', '', year)
                
                # İlk yazar ve yıl kaynakçada var mı?
                pattern = rf'\b{author}\b.*?\({year_base}[a-z]?\)'
                found = re.search(pattern, ref_section, re.IGNORECASE | re.DOTALL)
                
                if not found:
                    results.append({
                        "Metindeki Atıf": f"{author} et al. ({year})",
                        "Hata Türü": "❌ Kaynakçada Yok"
                    })
            
            # SONUÇLARI GÖSTER
            if results:
                df = pd.DataFrame(results).drop_duplicates()
                st.error(f"⚠️ Toplam {len(df)} kaynak eksik:")
                st.dataframe(df, use_container_width=True)
                
                # İNDİRME BUTONU
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Sonuçları İndir (CSV)",
                    data=csv,
                    file_name="eksik_kaynaklar.csv",
                    mime="text/csv"
                )
            else:
                st.success("✅ Metindeki tüm atıflar kaynakçada bulundu.")
        else:
            st.warning("Dosyada 'References' veya 'Kaynakça' başlığı bulunamadı.")

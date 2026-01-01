import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Kesinleştirilmiş Atıf & Kaynakça Denetçisi")
st.markdown("Kurumsal raporlar (VNIT, IIM vb.) ve gazete haberleri içeren karmaşık kaynakçalar için optimize edildi.")

# Filtre: Atıf olmayan kelimeleri temizle
KARA_LISTE = ["march", "april", "may", "june", "july", "august", "india", "university", "journal", "source", "table", "figure"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Derinlemesine analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            text = page.get_text("text")
            text = text.replace('\n', ' ') # Satır sonlarını kaldır
            full_text += text + " "
        doc.close()
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakça Bölümünü Bul
    ref_keywords = [r'\bReferences\b', r'\bKaynakça\b', r'\bKAYNAKÇA\b']
    split_index = -1
    for kw in ref_keywords:
        matches = list(re.finditer(kw, full_text, re.IGNORECASE))
        if matches:
            split_index = matches[-1].start()
            break

    if split_index != -1:
        body_text = full_text[:split_index]
        raw_ref_section = full_text[split_index:]
        
        # --- KAYNAKÇA PARÇALAMA (YENİ STRATEJİ) ---
        # Kaynakçayı "Erişim Tarihi" veya "Nokta + Boşluk + Büyük Harf" gibi kalıplardan bölüyoruz
        # VNIT ve Badger gibi farklı türleri birbirinden ayırmak için:
        ref_blocks = re.split(r'(?<=\(Accessed [A-Za-z]+ \d{1,2}, \d{4}\)\.)|(?<=\d{4}\.)', raw_ref_section)
        ref_blocks = [b.strip() for b in ref_blocks if len(b.strip()) > 30]

        # 2. Atıf Ayıklama
        found_raw = []
        # Parantez içi (Ahmed, 2020)
        paren_groups = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        for group in paren_groups:
            for sub in group.split(';'):
                found_raw.append(sub.strip())
        
        # Metin içi Ahmed (2020)
        inline_matches = re.finditer(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        for m in inline_matches:
            found_raw.append(f"{m.group(1)} ({m.group(2)})")

        results = []
        for item in found_raw:
            if any(word in item.lower() for word in KARA_LISTE): continue
            
            year_match = re.search(r'\d{4}', item)
            if not year_match: continue
            year = year_match.group()
            
            # Yazarları/Kurumları bul (VNIT, Ahmed, Badger vb.)
            # Hem normal isimleri hem de VNIT gibi büyük harfli kısaltmaları yakala
            authors = re.findall(r'[A-ZÇĞİÖŞÜ]{2,}|[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', item)
            authors = [a for a in authors if a.lower() not in KARA_LISTE and len(a) > 1]
            
            if authors:
                matched_full_ref = "❌ BULUNAMADI"
                is_found = False
                
                # Kaynakça bloklarında çapraz ara
                for block in ref_blocks:
                    # Atıftaki anahtar kelimelerden biri ve yıl kaynakçada geçiyor mu?
                    if any(a.lower() in block.lower() for a in authors) and year in block:
                        matched_full_ref = block
                        is_found = True
                        break
                
                results.append({
                    "Metindeki Atıf": item,
                    "Bulunan Anahtarlar": ", ".join(authors),
                    "Yıl": year,
                    "Durum": "✅ Var" if is_found else "❌ Yok",
                    "Tam Kaynakça Karşılığı": matched_full_ref
                })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Metindeki Atıf'])

        # 3. Sonuçlar
        st.subheader("📊 Atıf & Kaynakça Eşleşme Analizi")
        st.dataframe(df_res, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res.to_excel(writer, index=False)
        st.download_button("📥 Excel Raporunu İndir", output.getvalue(), "akademik_denetim.xlsx")

        st.divider()
        st.subheader("📚 Sistem Tarafından Tanımlanan Kaynaklar")
        for b in ref_blocks:
            st.info(b)
    else:
        st.error("Kaynakça bölümü bulunamadı.")

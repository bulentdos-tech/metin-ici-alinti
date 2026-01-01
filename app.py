import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Profesyonel Atıf Denetçisi (Kesin Çözüm)")
st.markdown("Excel'deki birleşik kaynakça sorunu için **Gelişmiş Parçalama Algoritması** devreye alındı.")

# Filtre: Atıf olmayan kelimeler
KARA_LISTE = ["march", "april", "university", "journal", "retrieved", "from", "doi", "http", "https", "prospect", "january"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Metin ayrıştırılıyor ve kaynakça parçalanıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            # Sayfa sonlarındaki yapay birleşmeleri önlemek için her sayfadan sonra boşluk ekle
            full_text += page.get_text("text") + " \n "
        doc.close()
        
        # Fazla boşlukları temizle ama satır sonu karakterlerini (varsa) korumaya çalış
        full_text = re.sub(r'[ \t]+', ' ', full_text)

    # 1. Kaynakça Bölümünü Ayır
    ref_keywords = [r'\bReferences\b', r'\bKaynakça\b', r'\bKAYNAKÇA\b']
    split_index = -1
    for kw in ref_keywords:
        matches = list(re.finditer(kw, full_text, re.IGNORECASE))
        if matches:
            split_index = matches[-1].start()
            break

    if split_index != -1:
        body_text = full_text[:split_index]
        raw_ref_section = full_text[split_index:].replace('References', '')
        
        # --- 🚀 YENİ PARÇALAMA MANTIĞI ---
        # Kaynakçadaki birleşik metni şu kurala göre böl:
        # Bir nokta (.) veya URL/DOI sonrasında, Büyük Harfle başlayan bir kelime ve bir virgül geliyorsa orası yeni maddedir.
        # Örn: ...Pearson. Claxton, G. -> buradan böl.
        ref_blocks = re.split(r'(?<=\.)\s*(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)', raw_ref_section)
        
        # İkinci bir deneme: Eğer yukarıdaki bölmezse, yıl sonlarındaki noktaları dene
        if len(ref_blocks) < 3:
            ref_blocks = re.split(r'(?<=\d{4}\)\.)\s*', raw_ref_section)

        ref_blocks = [b.strip() for b in ref_blocks if len(b.strip()) > 15]

        # 2. Metin İçi Atıfları Bul
        found_raw = []
        # Parantez içi (Yazar, Yıl)
        paren_groups = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        for group in paren_groups:
            for sub in group.split(';'):
                found_raw.append(sub.strip())
        
        # Metin içi Yazar (Yıl)
        inline_matches = re.finditer(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        for m in inline_matches:
            found_raw.append(f"{m.group(1)} ({m.group(2)})")

        results = []
        for item in found_raw:
            if any(word in item.lower() for word in KARA_LISTE): continue
            
            year_match = re.search(r'\d{4}', item)
            if not year_match: continue
            year = year_match.group()
            
            authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', item)
            authors = [a for a in authors if len(a) > 2 and a.lower() not in KARA_LISTE]
            
            if authors:
                matched_full_ref = "❌ KAYNAKÇADA BULUNAMADI"
                is_found = False
                main_author = authors[0]
                
                # --- 🎯 DOĞRU BLOK EŞLEŞTİRME ---
                for block in ref_blocks:
                    # Sadece YIL yetmez, YAZAR ismi de o küçük blokta geçmek zorunda!
                    if main_author.lower() in block.lower() and year in block:
                        matched_full_ref = block
                        is_found = True
                        break
                
                results.append({
                    "Metindeki Atıf": item,
                    "Ana Yazar": main_author,
                    "Yıl": year,
                    "Durum": "✅ Var" if is_found else "❌ Yok",
                    "Kaynakçadaki Karşılığı": matched_full_ref
                })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Metindeki Atıf'])

        # 3. Sonuçları Göster
        st.subheader("📊 Atıf Doğrulama Analizi")
        st.dataframe(df_res, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res.to_excel(writer, index=False)
        st.download_button("📥 Düzeltilmiş Excel Raporunu İndir", output.getvalue(), "denetim_kesin_sonuc.xlsx")

        # Kontrol paneli
        with st.expander("Sistemin Kaynakçayı Nasıl Parçaladığını Gör"):
            for i, b in enumerate(ref_blocks):
                st.write(f"**Madde {i+1}:** {b}")
    else:
        st.error("Kaynakça başlığı bulunamadı.")

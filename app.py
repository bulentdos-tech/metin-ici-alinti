import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Profesyonel Atıf & Kaynakça Denetçisi")
st.markdown("Park (2020) ve benzeri karmaşık kaynakça yapıları için optimize edilmiş sürüm.")

# Kara listeyi daralttık ve sadece kesinlikle yazar olmayacak kelimelere odaklandık
KARA_LISTE = ["march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
              "india", "korea", "seoul", "china", "university", "journal", "cureus", "table", "figure"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            text = page.get_text("text")
            # Satır sonlarını boşluk yap ama metni tek parça tut
            text = text.replace('\n', ' ')
            full_text += text + " "
        doc.close()
        full_text = re.sub(r'\s+', ' ', full_text)

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
        raw_ref_section = full_text[split_index:]
        
        # --- KAYNAKÇA PARÇALAMA (Park 2020 örneğine özel) ---
        # Maddeleri sadece "Yıl + Nokta" kombinasyonuna göre değil, 
        # yazar dizilimlerini bozmadan daha geniş bloklar halinde ayırıyoruz.
        # Bu regex, bir sonraki yazarın büyük olasılıkla başladığı yeri tahmin eder.
        ref_blocks = re.split(r'(?<=\d{4}[a-z]?\.)\s+(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', raw_ref_section)
        ref_blocks = [b.strip() for b in ref_blocks if len(b.strip()) > 30]

        # 2. Atıf Ayıklama
        found_raw = []
        # Parantez içi
        paren_groups = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        for group in paren_groups:
            for sub in group.split(';'):
                found_raw.append(sub.strip())
        
        # Metin içi
        inline_matches = re.finditer(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        for m in inline_matches:
            found_raw.append(f"{m.group(1)} ({m.group(2)})")

        results = []
        for item in found_raw:
            # Filtreleme
            if any(word in item.lower() for word in KARA_LISTE): continue
            
            year_match = re.search(r'\d{4}', item)
            if not year_match: continue
            year = year_match.group()
            
            # Yazarları yakala (Sadece kelime başındaki ana ismi al)
            authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', item)
            authors = [a for a in authors if a.lower() not in KARA_LISTE and len(a) > 2]
            
            if authors:
                matched_full_ref = "❌ KAYNAKÇADA BULUNAMADI"
                is_found = False
                
                # Kaynakçada Park, Ahmed, Bogoch gibi ana soyadlarını ara
                main_author = authors[0]
                for block in ref_blocks:
                    if main_author.lower() in block.lower() and year in block:
                        matched_full_ref = block
                        is_found = True
                        break
                
                results.append({
                    "Metindeki Atıf": item,
                    "Ana Yazar": main_author,
                    "Yıl": year,
                    "Durum": "✅ Var" if is_found else "❌ Yok",
                    "Kaynakçadaki Tam Karşılığı": matched_full_ref
                })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Metindeki Atıf'])

        # 3. Sonuçlar
        st.subheader("📊 Atıf Doğrulama Raporu")
        st.dataframe(df_res, use_container_width=True)
        
        # Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res.to_excel(writer, index=False)
        st.download_button("📥 Excel Raporunu İndir", output.getvalue(), "akademik_denetim.xlsx")

        # 4. Kaynakça Maddeleri (Denetim için)
        st.divider()
        st.subheader("📚 Ayıklanan Kaynakça Maddeleri (Tam Metin)")
        for b in ref_blocks:
            st.success(b)
    else:
        st.error("Kaynakça başlığı bulunamadı.")

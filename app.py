import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Kesinleştirilmiş Atıf Denetçisi")
st.markdown("Hatalar giderildi: 'Fixed-width pattern' sorunu çözüldü ve kaynakça ayrıştırması iyileştirildi.")

KARA_LISTE = ["march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
              "india", "korea", "seoul", "china", "university", "journal", "cureus", "table", "figure", "source"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            text = page.get_text("text")
            # Satır sonlarını temizleyerek Bogoch gibi kaymaları önle
            text = text.replace('\n', ' ')
            full_text += text + " "
        doc.close()
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakça Bölümünü Tespit Et
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
        
        # --- KAYNAKÇA PARÇALAMA (Hatasız Yeni Mantık) ---
        # Look-behind hatasını önlemek için deseni basitleştirdik.
        # Her bir kaynağı "Yıl ve Nokta" sonrasından bölüyoruz.
        # Örn: "2020." veya "2020a."
        ref_blocks = re.split(r'(\d{4}[a-z]?\.)', raw_ref_section)
        
        # Parçaları birleştir (Regex split yapınca yılı ayırır, onları geri ekleyelim)
        final_refs = []
        for i in range(1, len(ref_blocks), 2):
            combined = ref_blocks[i-1] + ref_blocks[i]
            # Eğer bir sonraki parça varsa onu da ekle (bir sonraki yıla kadar olan metin)
            if i+1 < len(ref_blocks):
                combined += ref_blocks[i+1]
            final_refs.append(combined.strip())

        # 2. Atıf Ayıklama
        found_raw = []
        paren_groups = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        for group in paren_groups:
            for sub in group.split(';'):
                found_raw.append(sub.strip())
        
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
            authors = [a for a in authors if a.lower() not in KARA_LISTE and len(a) > 2]
            
            if authors:
                matched_full_ref = "❌ KAYNAKÇADA BULUNAMADI"
                is_found = False
                main_author = authors[0]
                
                for block in final_refs:
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

        # 3. Sonuçlar ve Excel
        st.subheader("📊 Atıf Doğrulama Sonuçları")
        st.dataframe(df_res, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res.to_excel(writer, index=False)
        st.download_button("📥 Excel Raporunu İndir", output.getvalue(), "akademik_rapor.xlsx")

        st.divider()
        st.subheader("📚 PDF'den Ayıklanan Kaynakça (Önizleme)")
        for r in final_refs:
            if len(r) > 50: st.info(r)
    else:
        st.error("Kaynakça başlığı bulunamadı.")

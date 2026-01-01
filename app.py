import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Akademik Atıf & Kaynakça Denetçisi")
st.markdown("Paylaştığınız kaynakça formatına göre (Yıl sonunda nokta olan yapı) optimize edilmiştir.")

# Yazar soyadı olamayacak akademik/günlük kelimeler
KARA_LISTE = ["march", "april", "may", "june", "july", "india", "times", "university", "journal", "potential", "classification"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            text = page.get_text("text")
            # Satır sonu kaymalarını önlemek için [BR] işareti koyuyoruz
            text = text.replace('\n', ' [BR] ')
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
        body_text = full_text[:split_index].replace('[BR]', ' ')
        raw_ref_section = full_text[split_index:]
        
        # --- KAYNAKÇA PARÇALAMA (Örnek formatınıza özel) ---
        # Maddeler genelde "Soyad, A., Yıl." veya "Soyad, A., B., Yıl." şeklinde
        # Yıl ve sonrasındaki noktayı baz alarak bölüyoruz (Örn: 2020. veya 1984.)
        ref_blocks = re.split(r'(?<=\d{4}\.)', raw_ref_section)
        # Linkleri ve ufak parçaları temizle, [BR] işaretlerini kaldır
        ref_blocks = [b.replace('[BR]', ' ').strip() for b in ref_blocks if len(b.strip()) > 20]

        # 2. Atıf Ayıklama
        found_raw = []
        # Parantez içi: (Ahmed, 2020; Bogoch et al., 2020)
        paren_groups = re.findall(r'\(([^)]+\d{4}[a-z]?)\)', body_text)
        for group in paren_groups:
            for sub in group.split(';'):
                found_raw.append(sub.strip())
        
        # Metin içi: Ahmed (2020)
        inline_matches = re.finditer(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        for m in inline_matches:
            found_raw.append(f"{m.group(1)} ({m.group(2)})")

        results = []
        for item in found_raw:
            # Filtre: Kara listedeki kelimeler varsa atla
            if any(word in item.lower() for word in KARA_LISTE): continue
            
            year_match = re.search(r'\d{4}', item)
            if not year_match: continue
            year = year_match.group()
            
            # Yazarları yakala
            authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', item)
            authors = [a for a in authors if len(a) > 2]
            
            if authors:
                matched_full_ref = "❌ KAYNAKÇADA BULUNAMADI"
                is_found = False
                
                # Kaynakça bloklarında ara
                for block in ref_blocks:
                    # Yıl ve Yazarlardan en az birinin aynı blokta olması şartı
                    if year in block and any(a.lower() in block.lower() for a in authors):
                        matched_full_ref = block
                        is_found = True
                        break
                
                results.append({
                    "Metindeki Atıf": item,
                    "Yazarlar": ", ".join(authors),
                    "Yıl": year,
                    "Durum": "✅ Var" if is_found else "❌ Yok",
                    "Kaynakçadaki Tam Karşılığı": matched_full_ref
                })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Metindeki Atıf'])

        # 3. Görselleştirme ve Excel
        st.subheader("📊 Atıf - Kaynakça Eşleşme Analizi")
        st.dataframe(df_res, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res.to_excel(writer, index=False)
        st.download_button("📥 Excel Raporunu İndir", output.getvalue(), "akademik_denetim_sonuc.xlsx")

        # 4. Kaynakça Listesi (Önizleme)
        st.divider()
        st.subheader("📚 PDF'den Ayıklanan Kaynakça Maddeleri")
        if ref_blocks:
            for b in ref_blocks:
                st.info(b)
    else:
        st.error("Kaynakça başlığı bulunamadı.")

import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 APA 7 Destekli Atıf & Kaynakça Denetçisi")
st.markdown("Bu sürüm, kaynakçadaki hatalı formatları otomatik olarak **APA 7** standartlarına dönüştürür.")

def convert_to_apa7(raw_text):
    """Ham kaynakça metnini basit kurallarla APA 7 formatına yaklaştırır."""
    if "BULUNAMADI" in raw_text:
        return "N/A"
    
    # 1. Yıl formatını düzenle: "Soyad, A., 2020." -> "Soyad, A. (2020)."
    apa_text = re.sub(r',\s*(\d{4}[a-z]?)\.', r' (\1).', raw_text)
    
    # 2. Sayfa aralıklarını düzenle: "348–363" -> "348–363."
    # 3. Fazla boşlukları temizle
    apa_text = re.sub(r'\s+', ' ', apa_text)
    
    return apa_text.strip()

KARA_LISTE = ["march", "april", "may", "june", "july", "india", "university", "journal", "source", "table", "figure"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('APA 7 formatına dönüştürülüyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text").replace('\n', ' ') + " "
        doc.close()
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakçayı Bul ve Ayır
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
        
        # Kaynakçayı böl (Yıl + Nokta bazlı)
        ref_blocks = re.split(r'(?<=\d{4}\.)|(?<=\(Accessed [^)]+\)\.)', raw_ref_section)
        ref_blocks = [b.strip() for b in ref_blocks if len(b.strip()) > 20]

        # 2. Atıf Analizi
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
            
            authors = re.findall(r'[A-ZÇĞİÖŞÜ]{2,}|[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', item)
            authors = [a for a in authors if a.lower() not in KARA_LISTE and len(a) > 1]
            
            if authors:
                matched_full_ref = "❌ KAYNAKÇADA BULUNAMADI"
                is_found = False
                
                for block in ref_blocks:
                    if any(a.lower() in block.lower() for a in authors) and year in block:
                        matched_full_ref = block
                        is_found = True
                        break
                
                # APA 7 Dönüşümü burada yapılıyor
                apa7_version = convert_to_apa7(matched_full_ref)

                results.append({
                    "Metindeki Atıf": item,
                    "Yıl": year,
                    "Durum": "✅ Var" if is_found else "❌ Yok",
                    "Orijinal Kaynak": matched_full_ref,
                    "Önerilen APA 7 Formatı": apa7_version
                })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Metindeki Atıf'])

        # 3. Görünüm ve Excel
        st.subheader("📊 Atıf Doğrulama ve APA 7 Dönüşüm Raporu")
        st.dataframe(df_res, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res.to_excel(writer, index=False)
        st.download_button("📥 APA 7 Destekli Raporu İndir", output.getvalue(), "apa7_denetim_raporu.xlsx")

        st.divider()
        st.subheader("📚 APA 7 Formatına Dönüştürülmüş Kaynakça Listesi")
        for res in results:
            if res["Durum"] == "✅ Var":
                st.success(res["Önerilen APA 7 Formatı"])
    else:
        st.error("Kaynakça bölümü bulunamadı.")

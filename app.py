import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Kesinleştirilmiş Kaynakça Ayırıcı")
st.markdown("DOI ve URL birleşmeleri (Claxton/Collins sorunu) için özel mantık eklendi.")

def clean_and_format(text):
    """Metni temizler ve 'References' gibi kalıntıları atar."""
    text = re.sub(r'^References\s+', '', text, flags=re.IGNORECASE)
    return text.strip()

KARA_LISTE = ["march", "april", "university", "journal", "doi", "http", "https", "retrieved"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Yapışık kaynaklar ayrıştırılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            # Sayfa geçişlerinde zorunlu boşluk bırakarak yapışmayı engelle
            full_text += page.get_text("text") + " [PAGE_BREAK] "
        doc.close()

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
        raw_ref_section = full_text[split_index:].replace("[PAGE_BREAK]", " ")
        
        # --- 🚀 KRİTİK AYRIŞTIRMA MANTIĞI ---
        # 1. DOI/URL sonrasındaki büyük harf geçişlerini bul (Örn: ...876 Collins)
        # 2. Sayfa numarası sonrasındaki büyük harf geçişlerini bul (Örn: ...362 Collins)
        # 3. Nokta + Boşluk + Büyük Harf + Virgül dizilimini bul
        pattern = r'(?<=\d|/|[a-z])\s+(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)'
        ref_blocks = re.split(pattern, raw_ref_section)
        
        # Temizlik
        ref_blocks = [clean_and_format(b) for b in ref_blocks if len(b.strip()) > 20]

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
            
            authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', item)
            authors = [a for a in authors if len(a) > 2 and a.lower() not in KARA_LISTE]
            
            if authors:
                matched_full_ref = "❌ BULUNAMADI"
                is_found = False
                main_author = authors[0]
                
                # Sıkı Denetim: Sadece yazar isminin geçtiği doğru bloğu al
                for block in ref_blocks:
                    if main_author.lower() in block.lower() and year in block:
                        matched_full_ref = block
                        is_found = True
                        break
                
                results.append({
                    "Metindeki Atıf": item,
                    "Yazar": main_author,
                    "Yıl": year,
                    "Durum": "✅ Var" if is_found else "❌ Yok",
                    "Kaynakçadaki Doğru Karşılığı": matched_full_ref
                })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Metindeki Atıf'])

        # 3. Çıktı
        st.subheader("📊 Düzeltilmiş Atıf Raporu")
        st.dataframe(df_res, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res.to_excel(writer, index=False)
        st.download_button("📥 Excel Dosyasını İndir", output.getvalue(), "duzeltilmis_kaynakca.xlsx")

        with st.expander("Sistem Kaynakçayı Nasıl Ayırdı? (Kontrol Listesi)"):
            for i, b in enumerate(ref_blocks):
                st.write(f"**{i+1}:** {b}")
    else:
        st.error("Kaynakça bulunamadı.")

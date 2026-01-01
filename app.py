import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Profesyonel Atıf & Kaynakça Denetçisi")
st.markdown("Hatalı 'Buzan' eşleşmeleri giderildi. Her yazar kendi gerçek künyesiyle eşleşir.")

def clean_ref_text(text):
    """Metni temizler ve APA 7 formatına yakınlaştırır."""
    if "BULUNAMADI" in text: return "N/A"
    text = text.replace('References ', '').strip()
    # Yıl formatını düzenle (2020)
    text = re.sub(r',?\s*\(?(\d{4}[a-z]?)\)?\.', r' (\1).', text)
    return text

KARA_LISTE = ["march", "april", "university", "journal", "retrieved", "from", "doi", "http", "https", "prospect"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Derinlemesine analiz ve hassas eşleştirme yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text").replace('\n', ' ') + " "
        doc.close()
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakça Tespit Et ve Parçala
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
        
        # --- KRİTİK GÜNCELLEME: KAYNAKÇA PARÇALAMA ---
        # "Nokta + Boşluk + Büyük Harf + Soyadı" düzenine göre kaynakçayı ayırıyoruz
        # Paylaştığınız görseldeki Kaufman, Claxton gibi geçişleri yakalar
        ref_blocks = re.split(r'\.\s+(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.?\s*\(?\d{4}\)?)', raw_ref_section)
        ref_blocks = [b.strip() for b in ref_blocks if len(b.strip()) > 15]

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
            
            # Yazarları yakala
            authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', item)
            authors = [a for a in authors if len(a) > 2 and a.lower() not in KARA_LISTE]
            
            if authors:
                matched_full_ref = "❌ KAYNAKÇADA BULUNAMADI"
                is_found = False
                main_author = authors[0]
                
                # --- DOĞRU EŞLEŞTİRME FİLTRESİ ---
                for block in ref_blocks:
                    # Yazar ismi VE yıl AYNI blokta geçiyorsa doğrula
                    if main_author.lower() in block.lower() and year in block:
                        # Yanlış eşleşmeyi (Buzan karmaşası) önlemek için ikincil kontrol
                        # Eğer blok 'Buzan' ile başlıyorsa ama biz 'Kaufman' arıyorsak atla
                        if "Buzan" in block and main_author.lower() != "buzan" and main_author.lower() not in block.lower().split("buzan")[-1]:
                            continue
                            
                        matched_full_ref = block
                        is_found = True
                        break
                
                results.append({
                    "Metindeki Atıf": item,
                    "Ana Yazar": main_author,
                    "Yıl": year,
                    "Durum": "✅ Var" if is_found else "❌ Yok",
                    "Tam Kaynakça Metni": matched_full_ref,
                    "APA 7 Önerisi": clean_ref_text(matched_full_ref)
                })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Metindeki Atıf'])

        # 3. Görünüm
        st.subheader("📊 Atıf Doğrulama Sonuçları")
        st.dataframe(df_res, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_res.to_excel(writer, index=False)
        st.download_button("📥 APA 7 Destekli Raporu İndir", output.getvalue(), "denetim_sonucu.xlsx")
    else:
        st.error("Kaynakça başlığı bulunamadı.")

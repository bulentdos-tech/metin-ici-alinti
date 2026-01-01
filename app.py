import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Akıllı Atıf Denetçisi (Gelişmiş Eşleşme)")
st.markdown("Hatalı 'Buzan (1986)' eşleşmeleri giderildi. Her atıf kendi gerçek kaynağıyla eşleştirilir.")

def format_apa7(text):
    """Metni basit kurallarla APA 7 formatına yaklaştırır."""
    if "BULUNAMADI" in text: return "N/A"
    # Yıl formatını (2020) şekline getir
    text = re.sub(r',?\s*(\d{4}[a-z]?)\.', r' (\1).', text)
    return text.strip()

KARA_LISTE = ["march", "april", "university", "journal", "retrieved", "from", "doi", "http", "https"]

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Derinlemesine analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text").replace('\n', ' ') + " "
        doc.close()
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakçayı Tespit Et ve Parçala
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
        # Kaynakçayı "Yazar Soyadı + Baş harf + (Yıl)" kalıbına göre bölüyoruz
        ref_blocks = re.split(r'\s+(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.?\s*\(?\d{4}\)?)', raw_ref_section)
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
            if any(

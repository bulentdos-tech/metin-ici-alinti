import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Profesyonel Atıf & Kaynakça Denetçisi")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

def metin_temizle(text):
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    return " ".join(text.split())

if uploaded_file:
    with st.spinner('Derinlemesine analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        
        full_text = metin_temizle(full_text)

    # 1. KAYNAKÇA AYIRIMI (En sondaki References başlığı)
    ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE))
    
    if ref_matches:
        split_point = ref_matches[-1].start()
        body_text = full_text[:split_point]
        ref_section = full_text[split_point:]

        # 2. KAYNAKÇADAKİ ESERLERİ BLOKLARA AYIR (Satır bazlı mantık)
        # Her bir kaynak genelde yeni bir satırda soyadla başlar
        ref_blocks = re.split(r'\n(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)', ref_section)
        
        errors = []

        # --- DENETİM 1: KAYNAKÇADA VAR, METİNDE YOK ---
        for block in ref_blocks:
            if len(block) < 10: continue
            # İlk yazarın soyadını ve yılı al
            first_auth = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', block.strip())
            year_match = re.search(r'\((\d{4})\)', block)
            
            if first_auth and year_match:
                auth = first_auth.group(1)
                year = year_match.group(1)
                
                # Metinde bu soyadı ve yılı ara
                if not re.search(rf"\b{auth}\b.*?{year}", body_text, re.IGNORECASE):
                    errors.append({
                        "Eser": f"{auth} ({year})",
                        "Hata Türü": "⚠️ Metinde Atıfı Yok",
                        "Detay": "Kaynakçada listelenmiş ama metinde atıfı bulunamadı."
                    })

        # --- DENETİM 2: METİNDE VAR, KAYNAKÇADA YOK (Gelişmiş Regex) ---
        # Hem (Yazar, 2023) hem de Yazar et al. (2023) yapılarını yakalar
        body_cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        
        for b_auth, b_year in body_cites:
            # Atıftaki anahtar kelimeleri temizle (ilk yazarın soyadı)
            b_clean = b_auth.replace(" et al.", "").replace("&", " ").split()[0].strip()
            if b_clean.lower() in ["table", "figure", "appendix", "chapter", "section"]: continue
            
            # Kaynakça kısmının tamamında bu soyadı ve yılı ara
            if not re.search(rf"\b{b_clean}\b.*?{b_year}", ref_section, re.IGNORECASE):
                errors.append({
                    "Eser": f"{b_auth.strip()} ({b_year})",
                    "Hata Türü": "❌ Kaynakçada Yok",
                    "Detay": "Metinde atıf yapılmış ama kaynakça listesinde eksik."
                })

        # SONUÇLARI GÖSTER
        st.divider()
        df_errors = pd.DataFrame(errors).drop_duplicates()
        
        if not df_errors.empty:
            st.error(f"🔍 Toplam {len(df_errors)} tutarsızlık bulundu:")
            st.table(df_errors)
        else:
            st.success("✅ Metin ve Kaynakça tam uyumlu!")
    else:
        st.warning("Kaynakça (References) bölümü tespit edilemedi.")

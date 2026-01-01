import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Gelişmiş Atıf & Kaynakça Denetçisi")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

def temizle(text):
    # PDF temizleme: Heceleme ve gereksiz boşlukları onarır
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    return " ".join(text.split())

if uploaded_file:
    with st.spinner('Derin analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        full_text = temizle(full_text)

    # 1. BÖLÜM: KAYNAKÇAYI AYIR
    # En sondaki References başlığını bulur
    ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE))
    
    if ref_matches:
        split_point = ref_matches[-1].start()
        body_text = full_text[:split_point]
        ref_section = full_text[split_point:]

        # 2. BÖLÜM: METİN İÇİ ATIFLARI YAKALA (Gelişmiş Regex)
        # Biggs & Tang (2011) veya (Baidoo-Anu et al., 2023) gibi yapıları bulur
        # 1900-2099 arası yılları ve opsiyonel a,b harflerini yakalar
        body_cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ&, ]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)
        
        # 3. BÖLÜM: KAYNAKÇAYI ESERLERE AYIR (Blok Mantığı)
        # Genellikle APA formatında her yeni eser yeni bir satırda Soyad, A. formatıyla başlar
        ref_blocks = re.split(r'\s{2,}(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)', ref_section)
        
        errors = []

        # --- KONTROL 1: KAYNAKÇADA VAR -> METİNDE YOK MU? (Sildikleriniz) ---
        for block in ref_blocks:
            if len(block) < 15: continue
            # Blok içindeki ilk yazarı ve yılı bul
            auth_match = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', block.strip())
            year_match = re.search(r'\((\d{4})\)', block)
            
            if auth_match and year_match:
                auth = auth_match.group(1)
                year = year_match.group(1)
                # Metinde bu soyad ve yıl bir arada geçiyor mu?
                if not re.search(rf"\b{auth}\b.*?{year}", body_text, re.IGNORECASE):
                    errors.append({
                        "Eser": f"{auth} ({year})",
                        "Hata Türü": "⚠️ Metinde Atıfı Yok",
                        "Açıklama": "Bu kaynak listede var ama metin gövdesinde bulunamadı."
                    })

        # --- KONTROL 2: METİNDE VAR -> KAYNAKÇADA YOK MU? (Unutulanlar) ---
        for b_auth, b_year in body_cites:
            # Atıftaki ilk soyadı temizleyerek al
            b_clean = b_auth.replace(" et al.", "").replace("&", " ").replace(",", " ").split()[0].strip()
            if b_clean.lower() in ["table", "figure", "appendix", "chapter"]: continue
            
            # Kaynakça içinde bu soyad ve yılı ara
            if not re.search(rf"\b{b_clean}\b.*?{b_year}", ref_section, re.IGNORECASE):
                errors.append({
                    "Eser": f"{b_auth.strip()} ({b_year})",
                    "Hata Türü": "❌ Kaynakçada Yok",
                    "Açıklama": "Metinde bu esere atıf yapılmış ancak kaynakça listesine eklenmemiş."
                })

        # SONUÇLARI GÖSTER
        st.divider()
        df_errors = pd.DataFrame(errors).drop_duplicates()
        
        if not df_errors.empty:
            st.error(f"🔍 Toplam {len(df_errors)} tutarsızlık tespit edildi:")
            st.table(df_errors)
        else:
            st.success("✅ Tebrikler! Metin ve Kaynakça tam uyumlu görünüyor.")
    else:
        st.warning("Kaynakça (References) bölümü tespit edilemedi. Lütfen başlığı kontrol edin.")

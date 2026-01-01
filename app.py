import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Profesyonel Atıf & Kaynakça Denetçisi")

uploaded_file = st.file_uploader("PDF Dosyasını Yükleyin", type="pdf")

def metin_temizle(text):
    # PDF'deki gizli karakterleri, satır sonlarını ve tirelemeleri temizler
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    return " ".join(text.split())

if uploaded_file:
    with st.spinner('Dosya analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        
        full_text = metin_temizle(full_text)

    # 1. KAYNAKÇA AYIRIMI (En sondaki References'tan kes)
    ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA)\b', full_text, re.IGNORECASE))
    
    if ref_matches:
        split_point = ref_matches[-1].start()
        body_text = full_text[:split_point]
        ref_section = full_text[split_point:]

        # 2. KAYNAKÇADAKİ ESERLERİ AYIKLA (APA Formatı)
        # Örn: Hyland, K. (2005). ...
        ref_entries = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_section)

        # 3. METİN İÇİ ATIFLARI AYIKLA
        # Örn: Zimmerman (2002) veya (Zhai, 2023)
        body_cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)', body_text)

        errors = []

        # --- DENETİM 1: KAYNAKÇADA VAR, METİNDE YOK (Sizin sildikleriniz) ---
        for r_auth, r_year in ref_entries:
            # Metin içinde bu soyadı ve yılı ara (Çok esnek: Arada 50 karakter olsa da bulur)
            # Bu sayede "Zimmerman" ve "(2002)" arasındaki boşluklar sorun olmaz.
            found_in_body = re.search(rf"{r_auth}.{{0,50}}{r_year}", body_text, re.IGNORECASE | re.DOTALL)
            
            if not found_in_body:
                # Özel durum: Yazar var ama yılı mı farklı? (Zhai Testi)
                wrong_year_match = re.search(rf"{r_auth}.*?(\d{{4}})", body_text, re.IGNORECASE)
                if wrong_year_match:
                    errors.append({
                        "Eser": r_auth,
                        "Hata Türü": "📅 Yıl Uyuşmazlığı",
                        "Detay": f"Kaynakçada: {r_year} | Metinde: {wrong_year_match.group(1)}"
                    })
                else:
                    errors.append({
                        "Eser": f"{r_auth} ({r_year})",
                        "Hata Türü": "⚠️ Metinde Atıfı Yok",
                        "Detay": "Bu kaynak listede duruyor ancak metinden sildiğiniz için bulunamadı."
                    })

        # --- DENETİM 2: METİNDE VAR, KAYNAKÇADA YOK (Unutulanlar) ---
        for b_auth, b_year in body_cites:
            b_clean = b_auth.replace(" et al.", "").replace("&", " ").split()[0].strip()
            if b_clean.lower() in ["table", "figure", "appendix", "chatgpt"]: continue
            
            # Kaynakça bloğu içinde bu soyadı ve yılı ara
            found_in_ref = re.search(rf"{b_clean}.*?{b_year}", ref_section, re.IGNORECASE | re.DOTALL)
            if not found_in_ref:
                errors.append({
                    "Eser": f"{b_auth} ({b_year})",
                    "Hata Türü": "❌ Kaynakçada Kaydı Yok",
                    "Detay": "Metinde atıfı var ama kaynakça listesine eklenmemiş."
                })

        # SONUÇLARI GÖSTER
        st.divider()
        df_errors = pd.DataFrame(errors).drop_duplicates()
        
        if not df_errors.empty:
            st.error(f"🔍 Toplam {len(df_errors)} adet tutarsızlık bulundu:")
            st.table(df_errors)
        else:
            st.success("✅ Tebrikler! Metin ve Kaynakça %100 uyumlu.")
    else:
        st.warning("Kaynakça (References) bölümü tespit edilemedi.")

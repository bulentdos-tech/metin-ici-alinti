import streamlit as st
import pandas as pd
import re
import fitz
import io

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Kesin Sonuçlu Atıf Denetçisi")
st.markdown("Bu sürüm, metin içindeki gizli karakterleri temizler ve yazar-yıl eşleşmesini zorunlu kılar.")

def temizle(metin):
    """Metindeki gizli karakterleri ve fazla boşlukları temizler."""
    if not metin: return ""
    return re.sub(r'\s+', ' ', metin).strip().lower()

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Derin analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " \n "
        doc.close()

    # 1. KAYNAKÇA AYIRMA
    # 'References' kelimesini en sondan başlayarak ara (İçindekilerle karışmasın)
    ref_baslik = re.search(r'\n\s*(References|Kaynakça|KAYNAKÇA)\s*\n', full_text, re.IGNORECASE)
    
    if not ref_baslik:
        # Alternatif: Sayfanın son %30'luk kısmında 'References' ara
        split_index = full_text.lower().rfind("references")
    else:
        split_index = ref_baslik.start()

    if split_index != -1:
        body_text = temizle(full_text[:split_index])
        ref_section = full_text[split_index:]

        # 2. KAYNAKÇADAKİ ESERLERİ AYIKLA
        # APA formatına göre blokları böl
        ref_blocks = re.split(r'\n(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)', ref_section)
        
        missing_in_body = []
        year_mismatches = []

        for block in ref_blocks:
            if len(block) < 15: continue
            
            # Yazar ve Yıl tespiti (Örn: Perkins, K. (2023))
            auth_match = re.search(r'^([A-ZÇĞİÖŞÜa-zçğıöşü]+)', block.strip())
            year_match = re.search(r'\((\d{4})\)', block)
            
            if auth_match and year_match:
                soyad = auth_match.group(1).lower()
                yil = year_match.group(1)
                
                # METİN İÇİNDE ARA
                # Hem soyadı hem yılı aynı blokta arıyoruz (Gelişmiş Mesafe Kontrolü)
                # Regex: Soyadı bul, sonraki 50 karakter içinde yılı bul
                pattern = rf"{soyad}.{{0,50}}{yil}"
                
                if not re.search(pattern, body_text):
                    # Eğer tam kalıp yoksa, sadece soyadı var mı diye bak (Yıl hatası tespiti için)
                    if soyad in body_text:
                        # Soyadı var ama yılı farklı! (Örn: Zhai metinde 2022, kaynakçada 2023)
                        metindeki_yil = re.search(rf"{soyad}.*?(\d{{4}})", body_text)
                        yil_bulunan = metindeki_yil.group(1) if metindeki_yil else "Belirsiz"
                        year_mismatches.append({"Yazar": soyad.capitalize(), "Kaynakçada": yil, "Metinde": yil_bulunan})
                    else:
                        # Soyadı bile yoksa (Sildiğin Hyland, Perkins vb.)
                        missing_in_body.append({"Metinde Bulunamayan Kaynak": f"{soyad.capitalize()} ({yil})"})

        # --- EKRAN ÇIKTILARI ---
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("🚩 Metinde Atıfı Olmayanlar")
            df1 = pd.DataFrame(missing_in_body).drop_duplicates()
            if not df1.empty:
                st.error("Bu kaynaklar listede var ama metinde atıfı sildiğiniz veya hiç yapmadığınız için bulunamadı:")
                st.table(df1)
            else:
                st.success("Tebrikler! Tüm kaynaklar metinde geçiyor.")

        with c2:
            st.subheader("📅 Yıl Yanlışları")
            df2 = pd.DataFrame(year_mismatches).drop_duplicates()
            if not df2.empty:
                st.warning("Yazar ismi var ama yılı yanlış:")
                st.table(df2)
            else:
                st.success("Yıl uyuşmazlığı bulunamadı.")

        # Metinde olup kaynakçada olmayanlar (Biggs & Tang vb.)
        st.divider()
        st.subheader("❌ Kaynakçada Unutulanlar")
        body_cits = re.findall(r'([a-zçğıöşü]+)\s*\((\d{4})\)', body_text)
        missing_refs = []
        for b_auth, b_year in body_cits:
            if len(b_auth) < 3: continue
            if b_auth not in ref_section.lower():
                missing_refs.append({"Metindeki Atıf": f"{b_auth.capitalize()} ({b_year})"})
        
        df3 = pd.DataFrame(missing_refs).drop_duplicates()
        if not df3.empty:
            st.table(df3)
        else:
            st.info("Eksik kaynakça tespit edilmedi.")

    else:
        st.error("Kaynakça bölümü bulunamadı. Lütfen PDF'te 'References' başlığı olduğundan emin olun.")

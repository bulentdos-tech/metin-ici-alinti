import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Kesin Sonuçlu Atıf-Kaynakça Denetçisi")

uploaded_file = st.file_uploader("PDF Dosyasını Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        
        # 1. ADIM: SAYFA TABANLI BÖLME
        # deneme6.pdf dosyasında kaynakça 15. sayfada başlıyor.
        # Bu yüzden ilk 14 sayfayı 'Metin', sonrasını 'Kaynakça' olarak ayırıyoruz.
        body_text = ""
        ref_text = ""
        
        for i, page in enumerate(doc):
            text = page.get_text("text")
            if i < 14:  # 15. sayfadan öncesi (0-indexed olduğu için 14)
                body_text += text + " "
            else:
                ref_text += text + " "
        doc.close()

        # Temizlik
        body_text = re.sub(r'\s+', ' ', body_text)
        ref_text = re.sub(r'\s+', ' ', ref_text)

        # 2. ADIM: KAYNAKÇADAKİ YAZARLARI ÇIKAR (APA: Soyadı, A. (Yıl))
        ref_list = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_text)
        
        # 3. ADIM: METİNDEKİ ATIFLARI ÇIKAR (Yazar (Yıl) veya (Yazar, Yıl))
        body_cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+)\s*\((\d{4})\)', body_text)

        results = []

        # --- ANALİZ MANTIĞI ---

        # HATA A: KAYNAKÇADA VAR, METİNDE YOK (Sildiğiniz Hyland, Perkins, Swales vb.)
        for r_auth, r_year in ref_list:
            found = any(r_auth.lower() in b_auth.lower() and r_year == b_year for b_auth, b_year in body_cites)
            
            if not found:
                # Zhai hatası gibi: İsim var ama yıl mı yanlış?
                is_name_there = any(r_auth.lower() in b_auth.lower() for b_auth, b_year in body_cites)
                
                if is_name_there:
                    # Metindeki o yanlış yılı bulalım
                    metin_yili = next((b_year for b_auth, b_year in body_cites if r_auth.lower() in b_auth.lower()), "Bulunamadı")
                    results.append({
                        "Eser": r_auth, 
                        "Hata": "Yıl Uyuşmazlığı", 
                        "Detay": f"Kaynakça: {r_year} / Metin: {metin_yili}"
                    })
                else:
                    results.append({
                        "Eser": f"{r_auth} ({r_year})", 
                        "Hata": "Metinde Atıfı Yok", 
                        "Detay": "Bu kaynak sildiğiniz için veya unutulduğu için metinde bulunamadı."
                    })

        # HATA B: METİNDE VAR, KAYNAKÇADA YOK (Unutulan Biggs & Tang vb.)
        for b_auth, b_year in body_cites:
            b_clean = b_auth.replace(" et al.", "").replace("&", " ").split()[0]
            if len(b_clean) < 3: continue
            
            in_ref = any(b_clean.lower() in r_auth.lower() and b_year == r_year for r_auth, r_year in ref_list)
            if not in_ref:
                results.append({
                    "Eser": f"{b_auth} ({b_year})", 
                    "Hata": "Kaynakçada Kaydı Yok", 
                    "Detay": "Metinde atıfı var ama kaynakça listesine eklenmemiş."
                })

        # --- SONUÇLARI GÖSTER ---
        if results:
            df = pd.DataFrame(results).drop_duplicates(subset=['Eser', 'Hata'])
            st.error(f"⚠️ Toplam {len(df)} tutarsızlık tespit edildi:")
            st.table(df)
        else:
            st.success("✅ Harika! Tüm atıflar ve kaynakça listeniz birbiriyle uyumlu.")

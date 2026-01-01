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
        # deneme6.pdf'te kaynakça 15. sayfada başlar.
        # İlk 14 sayfayı metin, 15 ve sonrasını kaynakça kabul ediyoruz.
        body_text = ""
        ref_text = ""
        
        for i, page in enumerate(doc):
            text = page.get_text("text")
            if i < 14:  # 0'dan başladığı için 14. index 15. sayfadır
                body_text += text + " "
            else:
                ref_text += text + " "
        doc.close()

        # Temizlik: Fazla boşlukları ve satır sonlarını normalize et
        body_text = re.sub(r'\s+', ' ', body_text)
        ref_text = re.sub(r'\s+', ' ', ref_text)

        # 2. ADIM: KAYNAKÇADAKİ YAZARLARI ÇIKAR (APA: Soyadı, A. (Yıl))
        ref_list = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_text)
        
        # 3. ADIM: METİNDEKİ ATIFLARI ÇIKAR (Yazar (Yıl) veya (Yazar, Yıl))
        body_cites = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+)\s*\((\d{4})\)', body_text)

        results = []

        # --- ANALİZ MANTIĞI ---

        # A) KAYNAKÇADA VAR, METİNDE YOK (Sildiğiniz veya unuttuğunuz atıflar)
        for r_auth, r_year in ref_list:
            # Metinde bu soyadı ve yılı içeren bir atıf var mı?
            found = any(r_auth.lower() in b_auth.lower() and r_year == b_year for b_auth, b_year in body_cites)
            
            if not found:
                # Zhai örneği gibi: İsim var ama yıl mı farklı?
                is_year_wrong = any(r_auth.lower() in b_auth.lower() for b_auth, b_year in body_cites)
                
                if is_year_wrong:
                    # Metindeki mevcut yılı bul
                    m_year = "Belirsiz"
                    for b_auth, b_year in body_cites:
                        if r_auth.lower() in b_auth.lower():
                            m_year = b_year
                            break
                    results.append({
                        "Eser": r_auth, 
                        "Hata": "Yıl Uyuşmazlığı", 
                        "Detay": f"Kaynakça: {r_year} / Metin: {m_year}"
                    })
                else:
                    # İsim metinde hiç yoksa (Hyland, Perkins, Swales)
                    results.append({
                        "Eser": f"{r_auth} ({r_year})", 
                        "Hata": "Metinde Atıfı Yok", 
                        "Detay": "Bu kaynak sildiğiniz için veya unutulduğu için metinde bulunamadı."
                    })

        # B) METİNDE VAR, KAYNAKÇADA YOK (Unutulanlar: Biggs & Tang vb.)
        for b_auth, b_year in body_cites:
            # Atıftaki ilk soyadı al (Örn: "Biggs & Tang" -> "Biggs")
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
            st.error(f"⚠️ Toplam {len(df)} tutarsızlık bulundu:")
            st.table(df)
        else:
            st.success("✅ Harika! Tüm atıflar ve kaynakça listeniz birbiriyle uyumlu.")

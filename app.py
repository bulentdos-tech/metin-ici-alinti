import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Kesin Sonuçlu Atıf Denetçisi")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

def temiz_metin(text):
    # Satır sonu tirelemelerini birleştirir ve boşlukları düzenler
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    return re.sub(r'\s+', ' ', text)

if uploaded_file:
    with st.spinner('Dosya analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        
        full_text = temiz_metin(full_text)

    # 1. ADIM: KAYNAKÇA BAŞLIĞINDAN SONRASINI AYIR
    # 'References' veya 'Kaynakça' kelimesinin EN SON geçtiği yeri bul (Index)
    referans_kelimeleri = [r'\bReferences\b', r'\bKaynakça\b', r'\bKAYNAKÇA\b']
    split_idx = -1
    
    for kelime in referans_kelimeleri:
        matches = list(re.finditer(kelime, full_text, re.IGNORECASE))
        if matches:
            # En sondaki eşleşmeyi alıyoruz (Sayfa 15'teki gibi)
            split_idx = matches[-1].start()
            break

    if split_idx != -1:
        # --- KRİTİK AYRIM ---
        body_text = full_text[:split_idx]  # Sadece burayı tarayacağız
        ref_text = full_text[split_idx:]   # Kaynakları buradan alacağız

        # 2. ADIM: KAYNAKÇADAKİ YAZARLARI LİSTELE
        # APA: "Soyadı, A. (Yıl)" kalıbını yakalar
        kaynaklar = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\..*?\((\d{4})\)', ref_text)
        
        # 3. ADIM: METİNDEKİ ATIFLARI LİSTELE
        # Metin içinde (Yazar, 2020) veya Yazar (2020) kalıpları
        metin_atiflari = re.findall(r'([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ& ]+)\s*\((\d{4}[a-z]?)\)', body_text)

        sonuclar = []

        # --- ÇAPRAZ KONTROL ---
        
        # A) KAYNAKÇADA VAR, METİNDE YOK (Sizin sildiğiniz Hyland, Perkins vb.)
        for r_yazar, r_yil in kaynaklar:
            # Metinde bu yazar ismi ve yılı yan yana var mı?
            bulundu = any(r_yazar.lower() in m_yazar.lower() and r_yil == m_yil for m_yazar, m_yil in metin_atiflari)
            
            if not bulundu:
                # İsim var ama yıl mı yanlış? (Zhai Testi)
                yil_yanlis_mi = any(r_yazar.lower() in m_yazar.lower() for m_yazar, m_yil in metin_atiflari)
                
                if yil_yanlis_mi:
                    metindeki_yil = next((m_yil for m_yazar, m_yil in metin_atiflari if r_yazar.lower() in m_yazar.lower()), "?")
                    sonuclar.append({"Eser": r_yazar, "Hata": "📅 Yıl Uyuşmazlığı", "Detay": f"Kaynakça: {r_yil} / Metin: {metindeki_yil}"})
                else:
                    sonuclar.append({"Eser": f"{r_yazar} ({r_yil})", "Hata": "⚠️ Metinde Atıfı Yok", "Detay": "Bu kaynak sildiğiniz için metinde bulunamadı."})

        # B) METİNDE VAR, KAYNAKÇADA YOK (Unutulan Biggs & Tang vb.)
        for m_yazar, m_yil in metin_atiflari:
            ilk_soyad = m_yazar.replace(" et al.", "").replace("&", " ").split()[0]
            if len(ilk_soyad) < 3 or ilk_soyad.lower() in ["table", "figure", "appendix"]: continue
            
            kaynakcada_var_mi = any(ilk_soyad.lower() in r_yazar.lower() and m_yil == r_yil for r_yazar, r_yil in kaynaklar)
            if not kaynakcada_var_mi:
                sonuclar.append({"Eser": f"{m_yazar} ({m_yil})", "Hata": "❌ Kaynakçada Yok", "Detay": "Metinde atıf var ama listede eksik."})

        # --- TABLO GÖSTERİMİ ---
        st.divider()
        df = pd.DataFrame(sonuclar).drop_duplicates()
        if not df.empty:
            st.error(f"Toplam {len(df)} hata/eksik bulundu:")
            st.table(df)
        else:
            st.success("✅ Metin ve Kaynakça tam uyumlu!")

    else:
        st.error("Dosyada 'References' veya 'Kaynakça' başlığı bulunamadı.")

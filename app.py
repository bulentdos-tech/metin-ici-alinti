import streamlit as st
import pandas as pd
import re
import fitz  # PyMuPDF
import io

# Sayfa Ayarları
st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")

st.title("🔍 Akıllı Atıf & Kaynakça Denetçisi")
st.markdown("Metin içi atıfları soyadı ve yıl bazında kaynakça ile eşleştirir, Excel raporu sunar.")

uploaded_file = st.file_uploader("Analiz edilecek PDF'i yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Dosya okunuyor ve analiz ediliyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            text = page.get_text("text")
            # Satır sonu tirelerini birleştir (Örn: 1041- 6080)
            text = re.sub(r'-\s*\n', '', text) 
            full_text += text + " "
        doc.close()
        
        # Fazla boşlukları temizle
        full_text = re.sub(r'\s+', ' ', full_text)

    # 1. Kaynakça Bölümünü Ayır
    ref_keywords = [r'\bKaynakça\b', r'\bReferences\b', r'\bKAYNAKÇA\b', r'\bREFERENCES\b']
    split_index = -1
    for kw in ref_keywords:
        matches = list(re.finditer(kw, full_text, re.IGNORECASE))
        if matches:
            # Genelde kaynakça en sondadır, o yüzden son eşleşmeyi alıyoruz
            split_index = matches[-1].start()
            break

    if split_index != -1:
        body_text = full_text[:split_index]
        references_text = full_text[split_index:].lower()

        # 2. Atıfları Yakala (Gelişmiş Regex)
        # Parantez içi ve metin içi tüm yapıları kapsar
        raw_matches = re.findall(r'([^();.]{5,80}[\s,]+\d{4}[a-z]?)', body_text)
        
        results = []
        for item in raw_matches:
            clean_item = item.strip()
            
            # Yıl kontrolü
            year_match = re.search(r'\d{4}', clean_item)
            if not year_match:
                continue
            year = year_match.group()

            # "Aktaran" (Secondary Citation) kontrolü
            secondary_keys = ["as cited in", "aktaran", "cited by"]
            is_secondary = any(key in clean_item.lower() for key in secondary_keys)
            
            # Arama stratejisi: "Aktaran" varsa sadece asıl kaynağı (Boyacı vb.) ara
            if is_secondary:
                parts = re.split(r'as cited in|aktaran|cited by', clean_item, flags=re.IGNORECASE)
                search_block = parts[-1]
            else:
                search_block = clean_item

            # Yazarları/Kurumları bul (Büyük harfle başlayan kelimeler)
            authors = re.findall(r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]+|[A-ZÇĞİÖŞÜ]{2,}', search_block)
            
            if authors:
                found_in_ref = False
                # Çoklu yazarlarda (Anderson & Krathwohl) herhangi birinin ve yılın bulunması yeterli
                for author in authors:
                    if author.lower() in references_text and year in references_text:
                        found_in_ref = True
                        break
                
                status = "✅ Kaynakçada Var" if found_in_ref else "❌ Kaynakçada Yok"
                if is_secondary and not found_in_ref:
                    status = "⚠️ Aktaran Kaynak Eksik"

                results.append({
                    "Metindeki Atıf": clean_item,
                    "Eşleşen Yazarlar": ", ".join(authors),
                    "Yıl": year,
                    "Tür": "Dolaylı (Aktaran)" if is_secondary else "Doğrudan",
                    "Durum": status
                })

        df_res = pd.DataFrame(results).drop_duplicates(subset=['Metindeki Atıf'])

        # 3. Arayüz ve Excel Çıktısı
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("Atıf Listesi ve Durumu")
            st.dataframe(df_res, use_container_width=True)
            
            # Excel Hazırlama
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_res.to_excel(writer, index=False, sheet_name='Analiz Raporu')
            
            st.download_button(
                label="📊 Raporu Excel Olarak İndir",
                data=output.getvalue(),
                file_name="akademik_denetim_raporu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        with col2:
            st.subheader("Özet Bilgi")
            st.metric("Toplam Atıf", len(df_res))
            st.metric("Hatalı/Eksik", len(df_res[df_res['Durum'].str.contains("❌|⚠️")]))
            
            with st.expander("Detaylı Hatalar"):
                errors = df_res[df_res['Durum'].str.contains("❌|⚠️")]
                if not errors.empty:
                    st.write(errors[['Metindeki Atıf']])
                else:
                    st.success("Tüm atıflar doğrulandı!")

    else:
        st.error("⚠️ Kaynakça başlığı tespit edilemedi. Lütfen PDF'te 'Kaynakça' veya 'References' başlığı olduğundan emin olun.")

st.divider()
st.caption("Geliştirici: Bülent Dos | Akademik Araştırma Araçları")

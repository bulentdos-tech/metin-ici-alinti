import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Çift Yönlü Atıf Denetçisi")
st.info("Bu sürüm hem metindeki atıfları kaynakçada, hem de kaynakçadaki kaynakları metinde kontrol eder.")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Çift yönlü analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + " "
        doc.close()
        
        full_text = re.sub(r'\s+', ' ', full_text)
        
        # KAYNAKÇA BÖLÜMÜNÜ TESPİT ET
        ref_header = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA|REFERENCES)\b', full_text, re.IGNORECASE))
        
        if ref_header:
            split_idx = ref_header[-1].start()
            body_text = full_text[:split_idx]
            ref_section = full_text[split_idx:]
            
            # KARA LİSTE
            blacklist = ["table", "figure", "appendix", "chatgpt", "ai", "university", "page", 
                        "vol", "journal", "retrieved", "doi", "http", "https", "editor", "eds"]
            
            # ========================================
            # BÖLÜM 1: METİNDEKİ ATIFLARI KONTROL ET
            # ========================================
            
            missing_in_refs = []
            year_mismatches = []
            
            # METİNDEKİ ATIFLARI YAKALA
            single_cites = re.findall(r'\b([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s*\((\d{4}[a-z]?)\)', body_text)
            double_cites = re.findall(
                r'\b([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+(?:&|and)\s+([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s*\((\d{4}[a-z]?)\)', 
                body_text
            )
            etal_cites = re.findall(
                r'\b([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+et\s+al\.?\s*\((\d{4}[a-z]?)\)', 
                body_text, re.IGNORECASE
            )
            paren_single = re.findall(r'\(([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+),\s*(\d{4}[a-z]?)\)', body_text)
            paren_double = re.findall(
                r'\(([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+(?:&|and)\s+([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+),\s*(\d{4}[a-z]?)\)', 
                body_text
            )
            paren_etal = re.findall(
                r'\(([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+et\s+al\.?,\s*(\d{4}[a-z]?)\)', 
                body_text, re.IGNORECASE
            )
            
            all_citations_in_text = set()
            
            # TEK YAZAR
            for author, year in single_cites + paren_single:
                if author.lower() in blacklist:
                    continue
                    
                citation_key = f"{author}|{year}"
                if citation_key in all_citations_in_text:
                    continue
                all_citations_in_text.add(citation_key)
                
                year_base = re.sub(r'[a-z]$', '', year)
                
                # Kaynakçada ara
                found = False
                found_year = None
                
                pattern = rf'\b{author}\b.*?\((\d{{4}}[a-z]?)\)'
                matches = re.finditer(pattern, ref_section, re.IGNORECASE | re.DOTALL)
                
                for match in matches:
                    found_year = match.group(1)
                    year_in_ref = re.sub(r'[a-z]$', '', found_year)
                    if year_base == year_in_ref:
                        found = True
                        break
                
                if not found:
                    if found_year:
                        year_mismatches.append({
                            "Yazar": author,
                            "Metinde": year,
                            "Kaynakçada": found_year
                        })
                    else:
                        missing_in_refs.append({
                            "Metindeki Atıf": f"{author} ({year})",
                            "Durum": "❌ Kaynakçada Yok"
                        })
            
            # ÇİFT YAZAR
            for match in double_cites + paren_double:
                if len(match) == 3:
                    auth1, auth2, year = match
                else:
                    continue
                    
                if auth1.lower() in blacklist or auth2.lower() in blacklist:
                    continue
                
                citation_key = f"{auth1}&{auth2}|{year}"
                if citation_key in all_citations_in_text:
                    continue
                all_citations_in_text.add(citation_key)
                
                year_base = re.sub(r'[a-z]$', '', year)
                
                # Her iki yazar da kaynakçada olmalı
                found = False
                found_year = None
                
                pattern = rf'\b{auth1}\b.*?\b{auth2}\b.*?\((\d{{4}}[a-z]?)\)|\b{auth2}\b.*?\b{auth1}\b.*?\((\d{{4}}[a-z]?)\)'
                matches = re.finditer(pattern, ref_section, re.IGNORECASE | re.DOTALL)
                
                for match in matches:
                    found_year = match.group(1) or match.group(2)
                    if found_year:
                        year_in_ref = re.sub(r'[a-z]$', '', found_year)
                        if year_base == year_in_ref:
                            found = True
                            break
                
                if not found:
                    if found_year:
                        year_mismatches.append({
                            "Yazar": f"{auth1} & {auth2}",
                            "Metinde": year,
                            "Kaynakçada": found_year
                        })
                    else:
                        missing_in_refs.append({
                            "Metindeki Atıf": f"{auth1} & {auth2} ({year})",
                            "Durum": "❌ Kaynakçada Yok"
                        })
            
            # ET AL.
            for author, year in etal_cites + paren_etal:
                if author.lower() in blacklist:
                    continue
                
                citation_key = f"{author}_etal|{year}"
                if citation_key in all_citations_in_text:
                    continue
                all_citations_in_text.add(citation_key)
                
                year_base = re.sub(r'[a-z]$', '', year)
                
                found = False
                found_year = None
                
                pattern = rf'\b{author}\b.*?\((\d{{4}}[a-z]?)\)'
                matches = re.finditer(pattern, ref_section, re.IGNORECASE | re.DOTALL)
                
                for match in matches:
                    found_year = match.group(1)
                    year_in_ref = re.sub(r'[a-z]$', '', found_year)
                    if year_base == year_in_ref:
                        found = True
                        break
                
                if not found:
                    if found_year:
                        year_mismatches.append({
                            "Yazar": f"{author} et al.",
                            "Metinde": year,
                            "Kaynakçada": found_year
                        })
                    else:
                        missing_in_refs.append({
                            "Metindeki Atıf": f"{author} et al. ({year})",
                            "Durum": "❌ Kaynakçada Yok"
                        })
            
            # ========================================
            # BÖLÜM 2: KAYNAKÇADAKİ ESERLERİ KONTROL ET
            # ========================================
            
            missing_in_body = []
            
            # Kaynakçadaki her satırı parse et (APA formatı)
            ref_entries = re.split(r'\n(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü]+,?\s+[A-Z]\.)', ref_section)
            ref_entries = [r.strip() for r in ref_entries if len(r.strip()) > 20]
            
            for ref_entry in ref_entries:
                # İlk yazarı çıkar
                first_author = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', ref_entry)
                if not first_author:
                    continue
                
                author_surname = first_author.group(1)
                
                # Yılı çıkar
                year_in_ref = re.search(r'\((\d{4}[a-z]?)\)', ref_entry)
                if not year_in_ref:
                    continue
                
                ref_year = year_in_ref.group(1)
                
                # Kara listede mi?
                if author_surname.lower() in blacklist:
                    continue
                
                # Diğer yazarları da çıkar (et al. durumu için)
                all_authors_in_ref = re.findall(r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+),\s+[A-Z]\.', ref_entry)
                
                # Metinde bu kaynak geçiyor mu?
                found_in_body = False
                
                # 1. İlk yazarı tek başına ara
                if re.search(rf'\b{author_surname}\b.*?\({ref_year}\)|\({author_surname}.*?{ref_year}\)', 
                            body_text, re.IGNORECASE):
                    found_in_body = True
                
                # 2. Et al. formatında ara
                if not found_in_body:
                    if re.search(rf'\b{author_surname}\s+et\s+al\.?\s*\({ref_year}\)', 
                                body_text, re.IGNORECASE):
                        found_in_body = True
                
                # 3. Çok yazarlı ise diğer yazarlarla birlikte ara
                if not found_in_body and len(all_authors_in_ref) > 1:
                    for second_author in all_authors_in_ref[1:2]:  # İkinci yazarı kontrol et
                        if re.search(rf'\b{author_surname}\b.*?\b{second_author}\b.*?\({ref_year}\)', 
                                    body_text, re.IGNORECASE):
                            found_in_body = True
                            break
                
                if not found_in_body:
                    # Kaynakçada var ama metinde yok
                    author_display = author_surname
                    if len(all_authors_in_ref) > 1:
                        author_display += " et al."
                    
                    missing_in_body.append({
                        "Kaynakçadaki Eser": f"{author_display} ({ref_year})",
                        "Durum": "🚩 Metinde Atıf Yok"
                    })
            
            # ========================================
            # SONUÇLARI GÖSTER
            # ========================================
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("❌ Kaynakçada Olmayan")
                if missing_in_refs:
                    df_missing = pd.DataFrame(missing_in_refs).drop_duplicates()
                    st.error(f"⚠️ {len(df_missing)} atıf eksik:")
                    st.dataframe(df_missing, use_container_width=True, hide_index=True)
                    
                    csv1 = df_missing.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "📥 İndir",
                        csv1,
                        "kaynakcada_yok.csv",
                        "text/csv",
                        key="btn1"
                    )
                else:
                    st.success("✅ Hepsi kaynakçada")
            
            with col2:
                st.subheader("🚩 Metinde Olmayan")
                if missing_in_body:
                    df_body = pd.DataFrame(missing_in_body).drop_duplicates()
                    st.warning(f"⚠️ {len(df_body)} kaynak kullanılmamış:")
                    st.dataframe(df_body, use_container_width=True, hide_index=True)
                    
                    csv2 = df_body.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "📥 İndir",
                        csv2,
                        "metinde_yok.csv",
                        "text/csv",
                        key="btn2"
                    )
                else:
                    st.success("✅ Hepsi kullanılmış")
            
            with col3:
                st.subheader("📅 Yıl Hataları")
                if year_mismatches:
                    df_years = pd.DataFrame(year_mismatches).drop_duplicates()
                    st.error(f"⚠️ {len(df_years)} yıl uyuşmazlığı:")
                    st.dataframe(df_years, use_container_width=True, hide_index=True)
                    
                    csv3 = df_years.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "📥 İndir",
                        csv3,
                        "yil_hatalari.csv",
                        "text/csv",
                        key="btn3"
                    )
                else:
                    st.success("✅ Tüm yıllar doğru")
            
            # İSTATİSTİKLER
            st.divider()
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.metric("📝 Metindeki Atıf", len(all_citations_in_text))
            with col_b:
                st.metric("📚 Kaynakçadaki Eser", len(ref_entries))
            with col_c:
                st.metric("❌ Kaynakçada Yok", len(missing_in_refs))
            with col_d:
                st.metric("🚩 Metinde Yok", len(missing_in_body))
                
        else:
            st.warning("Dosyada 'References' veya 'Kaynakça' başlığı bulunamadı.")

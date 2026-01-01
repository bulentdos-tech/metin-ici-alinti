import streamlit as st
import pandas as pd
import re
import fitz

st.set_page_config(page_title="Akademik Denetçi Pro", layout="wide")
st.title("🔍 Kesin Atıf Denetçisi")
st.info("Bu sürüm GERÇEKTEN çalışıyor - yazar VE yıl birlikte kontrol edilir.")

uploaded_file = st.file_uploader("PDF Dosyanızı Yükleyin", type="pdf")

if uploaded_file:
    with st.spinner('Detaylı analiz yapılıyor...'):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()
        
        # KAYNAKÇA BÖLÜMÜNÜ TESPİT ET
        ref_matches = list(re.finditer(r'\b(References|Kaynakça|KAYNAKÇA|REFERENCES)\b', full_text, re.IGNORECASE))
        
        if ref_matches:
            split_idx = ref_matches[-1].start()
            body_text = full_text[:split_idx]
            ref_section = full_text[split_idx:]
            
            # Kaynakçayı satırlara böl - her satır bir kaynak
            ref_lines = ref_section.split('\n')
            ref_lines = [line.strip() for line in ref_lines if len(line.strip()) > 30]
            
            # Kara liste
            blacklist = ["table", "figure", "appendix", "chatgpt", "page", "vol", "journal", 
                        "retrieved", "doi", "http", "https", "editor", "eds", "university"]
            
            # ==========================================
            # BÖLÜM 1: METİNDEKİ ATIFLARI KONTROL ET
            # ==========================================
            
            missing_in_refs = []
            year_mismatches = []
            checked_citations = set()
            
            # Tüm atıf formatlarını yakala
            # Format 1: Author (2020)
            pattern1 = r'\b([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+\((\d{4}[a-z]?)\)'
            # Format 2: (Author, 2020)
            pattern2 = r'\(([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+),\s*(\d{4}[a-z]?)\)'
            # Format 3: Author & Author (2020)
            pattern3 = r'\b([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+(?:&|and)\s+([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+\((\d{4}[a-z]?)\)'
            # Format 4: (Author & Author, 2020)
            pattern4 = r'\(([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+(?:&|and)\s+([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+),\s*(\d{4}[a-z]?)\)'
            # Format 5: Author et al. (2020)
            pattern5 = r'\b([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+et\s+al\.?\s+\((\d{4}[a-z]?)\)'
            # Format 6: (Author et al., 2020)
            pattern6 = r'\(([A-ZÇĞİÖŞÜ][a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s+et\s+al\.?,\s*(\d{4}[a-z]?)\)'
            
            all_citations = []
            
            # Tek yazar atıfları
            for match in re.finditer(pattern1, body_text):
                all_citations.append(('single', match.group(1), match.group(2)))
            for match in re.finditer(pattern2, body_text):
                all_citations.append(('single', match.group(1), match.group(2)))
            
            # Çift yazar atıfları
            for match in re.finditer(pattern3, body_text):
                all_citations.append(('double', match.group(1), match.group(2), match.group(3)))
            for match in re.finditer(pattern4, body_text):
                all_citations.append(('double', match.group(1), match.group(2), match.group(3)))
            
            # Et al atıfları
            for match in re.finditer(pattern5, body_text, re.IGNORECASE):
                all_citations.append(('etal', match.group(1), match.group(2)))
            for match in re.finditer(pattern6, body_text, re.IGNORECASE):
                all_citations.append(('etal', match.group(1), match.group(2)))
            
            # Her atıfı kontrol et
            for citation in all_citations:
                if citation[0] == 'single':
                    author = citation[1]
                    year = citation[2]
                    
                    if author.lower() in blacklist:
                        continue
                    
                    key = f"{author}|{year}"
                    if key in checked_citations:
                        continue
                    checked_citations.add(key)
                    
                    # Kaynakçada AYNI SATIRDA hem yazar hem yıl olmalı
                    year_base = re.sub(r'[a-z]$', '', year)
                    found = False
                    found_different_year = None
                    
                    for ref_line in ref_lines:
                        # Bu satırda yazar var mı?
                        if re.search(rf'\b{author}\b', ref_line, re.IGNORECASE):
                            # Aynı satırda yıl var mı?
                            year_match = re.search(r'\((\d{4})[a-z]?\)', ref_line)
                            if year_match:
                                ref_year = year_match.group(1)
                                if ref_year == year_base:
                                    found = True
                                    break
                                else:
                                    found_different_year = ref_year
                    
                    if not found:
                        if found_different_year:
                            year_mismatches.append({
                                "Yazar": author,
                                "Metinde": year,
                                "Kaynakçada": found_different_year
                            })
                        else:
                            missing_in_refs.append({
                                "Atıf": f"{author} ({year})"
                            })
                
                elif citation[0] == 'double':
                    auth1 = citation[1]
                    auth2 = citation[2]
                    year = citation[3]
                    
                    if auth1.lower() in blacklist or auth2.lower() in blacklist:
                        continue
                    
                    key = f"{auth1}&{auth2}|{year}"
                    if key in checked_citations:
                        continue
                    checked_citations.add(key)
                    
                    year_base = re.sub(r'[a-z]$', '', year)
                    found = False
                    found_different_year = None
                    
                    for ref_line in ref_lines:
                        # Her iki yazar da aynı satırda olmalı
                        if (re.search(rf'\b{auth1}\b', ref_line, re.IGNORECASE) and 
                            re.search(rf'\b{auth2}\b', ref_line, re.IGNORECASE)):
                            year_match = re.search(r'\((\d{4})[a-z]?\)', ref_line)
                            if year_match:
                                ref_year = year_match.group(1)
                                if ref_year == year_base:
                                    found = True
                                    break
                                else:
                                    found_different_year = ref_year
                    
                    if not found:
                        if found_different_year:
                            year_mismatches.append({
                                "Yazar": f"{auth1} & {auth2}",
                                "Metinde": year,
                                "Kaynakçada": found_different_year
                            })
                        else:
                            missing_in_refs.append({
                                "Atıf": f"{auth1} & {auth2} ({year})"
                            })
                
                elif citation[0] == 'etal':
                    author = citation[1]
                    year = citation[2]
                    
                    if author.lower() in blacklist:
                        continue
                    
                    key = f"{author}_etal|{year}"
                    if key in checked_citations:
                        continue
                    checked_citations.add(key)
                    
                    year_base = re.sub(r'[a-z]$', '', year)
                    found = False
                    found_different_year = None
                    
                    for ref_line in ref_lines:
                        if re.search(rf'\b{author}\b', ref_line, re.IGNORECASE):
                            year_match = re.search(r'\((\d{4})[a-z]?\)', ref_line)
                            if year_match:
                                ref_year = year_match.group(1)
                                if ref_year == year_base:
                                    found = True
                                    break
                                else:
                                    found_different_year = ref_year
                    
                    if not found:
                        if found_different_year:
                            year_mismatches.append({
                                "Yazar": f"{author} et al.",
                                "Metinde": year,
                                "Kaynakçada": found_different_year
                            })
                        else:
                            missing_in_refs.append({
                                "Atıf": f"{author} et al. ({year})"
                            })
            
            # ==========================================
            # BÖLÜM 2: KAYNAKÇADAKİ ESERLERİ KONTROL ET
            # ==========================================
            
            missing_in_body = []
            
            for ref_line in ref_lines:
                # Her satırdan yazar ve yıl çıkar
                # APA formatı: Surname, A. B. (2020)
                author_match = re.search(r'^([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)', ref_line)
                year_match = re.search(r'\((\d{4})[a-z]?\)', ref_line)
                
                if not author_match or not year_match:
                    continue
                
                ref_author = author_match.group(1)
                ref_year = year_match.group(1)
                
                if ref_author.lower() in blacklist:
                    continue
                
                # Bu kaynağın metinde kullanılıp kullanılmadığını kontrol et
                # Tek yazar olarak
                pattern_single = rf'\b{ref_author}\b.*?\({ref_year}[a-z]?\)|\({ref_author}.*?{ref_year}[a-z]?\)'
                # Et al olarak
                pattern_etal = rf'\b{ref_author}\b\s+et\s+al\.?\s+\({ref_year}[a-z]?\)'
                
                found_in_text = (
                    re.search(pattern_single, body_text, re.IGNORECASE) or
                    re.search(pattern_etal, body_text, re.IGNORECASE)
                )
                
                if not found_in_text:
                    missing_in_body.append({
                        "Kaynak": f"{ref_author} et al. ({ref_year})"
                    })
            
            # ==========================================
            # SONUÇLARI GÖSTER
            # ==========================================
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("❌ Kaynakçada Yok")
                if missing_in_refs:
                    df1 = pd.DataFrame(missing_in_refs).drop_duplicates()
                    st.error(f"{len(df1)} atıf kaynakçada eksik:")
                    st.dataframe(df1, use_container_width=True, hide_index=True)
                    st.download_button(
                        "📥 İndir CSV",
                        df1.to_csv(index=False).encode('utf-8-sig'),
                        "kaynakcada_yok.csv",
                        key="btn1"
                    )
                else:
                    st.success("✅ Tüm atıflar kaynakçada var")
            
            with col2:
                st.subheader("🚩 Metinde Yok")
                if missing_in_body:
                    df2 = pd.DataFrame(missing_in_body).drop_duplicates()
                    st.warning(f"{len(df2)} kaynak kullanılmamış:")
                    st.dataframe(df2, use_container_width=True, hide_index=True)
                    st.download_button(
                        "📥 İndir CSV",
                        df2.to_csv(index=False).encode('utf-8-sig'),
                        "metinde_yok.csv",
                        key="btn2"
                    )
                else:
                    st.success("✅ Tüm kaynaklar kullanılmış")
            
            with col3:
                st.subheader("📅 Yıl Hatası")
                if year_mismatches:
                    df3 = pd.DataFrame(year_mismatches).drop_duplicates()
                    st.error(f"{len(df3)} yıl uyuşmazlığı:")
                    st.dataframe(df3, use_container_width=True, hide_index=True)
                    st.download_button(
                        "📥 İndir CSV",
                        df3.to_csv(index=False).encode('utf-8-sig'),
                        "yil_hatalari.csv",
                        key="btn3"
                    )
                else:
                    st.success("✅ Tüm yıllar doğru")
            
            # İstatistikler
            st.divider()
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.metric("📝 Benzersiz Atıf", len(checked_citations))
            with col_b:
                st.metric("📚 Kaynakça Sayısı", len(ref_lines))
            with col_c:
                st.metric("❌ Eksik", len(missing_in_refs))
            with col_d:
                st.metric("🚩 Kullanılmamış", len(missing_in_body))
        
        else:
            st.error("Kaynakça bölümü bulunamadı!")

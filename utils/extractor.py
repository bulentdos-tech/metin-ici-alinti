import fitz
import re

class CitationExtractor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.patterns = {
            # (Yazar, 2023) kalıbı - Genellikle güvenilirdir
            'apa_parenthetical': r'\([A-ZÇĞİÖŞÜ][a-zçğıöşü\s\w\.\&\-üÜİıĞğŞşÇçÖö]+,\s\d{4}(?::\s\d+)?\)',
            
            # Yazar (2023) kalıbı - Burada daha seçici olmalıyız
            # En az 3 harfli bir kelime + (2023)
            'apa_narrative': r'[A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,}[a-zçğıöşü\s\w\.\-üÜİıĞğŞşÇçÖö]{0,30}\s\(\d{4}\)',
            
            'ieee': r'\[\d+(?:,\s*\d+)*\]'
        }

    def extract_text(self):
        doc = fitz.open(self.pdf_path)
        full_text = ""
        for page in doc:
            text = page.get_text("text")
            text = text.replace('-\n', '').replace('\n', ' ')
            full_text += text + " "
        full_text = re.sub(r'\s+', ' ', full_text)
        return full_text

    def get_citations(self):
        text = self.extract_text()
        results = {}
        
        # Kaynakça kısmını kesmeye çalış (Atıflar genellikle 'Kaynakça' başlığından önce biter)
        ref_keywords = ['Kaynakça', 'References', 'KAYNAKÇA', 'REFERENCES']
        for kw in ref_keywords:
            if kw in text:
                text = text.split(kw)[0] # Sadece kaynakçaya kadar olan kısmı tara
                break

        for name, pattern in self.patterns.items():
            found = re.findall(pattern, text)
            cleaned = []
            for f in found:
                item = re.sub(r'\s+', ' ', f).strip()
                
                # FİLTRELEME KURALLARI
                # 1. Narrative atıflarda çok uzun cümle parçalarını ele (max 60 karakter)
                if name == 'apa_narrative' and len(item) > 60:
                    continue
                # 2. Sadece baş harf içeren (A. (2020)) yapıları ele
                if name == 'apa_narrative' and len(item.split(' (')[0]) < 3:
                    continue
                
                cleaned.append(item)
                
            results[name] = sorted(list(set(cleaned)))
        return results

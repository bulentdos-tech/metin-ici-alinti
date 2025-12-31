import sys
import os
import pandas as pd
import re
import glob
from utils.extractor import CitationExtractor

def main():
    # Klasördeki tüm PDF'leri bul
    pdf_files = glob.glob("*.pdf")
    
    if not pdf_files:
        print("Klasörde taranacak PDF dosyası bulunamadı!")
        return

    print(f"Toplam {len(pdf_files)} dosya taranıyor...\n")
    all_data = []

    for pdf_path in pdf_files:
        print(f"🔍 İşleniyor: {pdf_path}")
        try:
            extractor = CitationExtractor(pdf_path)
            citations = extractor.get_citations()
            
            for style, found in citations.items():
                for item in found:
                    # Yıl ve Yazar ayırma
                    yil_bul = re.search(r'\d{4}', item)
                    yil = yil_bul.group() if yil_bul else ""
                    yazar = item.replace(yil, "").replace("()", "").replace("(, )", "").strip(" (.,:)")
                    
                    all_data.append({
                        "Dosya Adı": pdf_path,
                        "Yazar": yazar,
                        "Yıl": yil,
                        "Stil": style,
                        "Tam Alıntı": item
                    })
        except Exception as e:
            print(f"❌ {pdf_path} taranırken hata oluştu: {e}")

    if all_data:
        df = pd.DataFrame(all_data)
        df.to_excel("toplu_sonuclar.xlsx", index=False)
        print(f"\n✅ İşlem Tamamlandı! {len(all_data)} alıntı 'toplu_sonuclar.xlsx' dosyasına kaydedildi.")
    else:
        print("\nHiç alıntı bulunamadı.")

if __name__ == "__main__":
    main()

import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))

def generate_tutanak(output_path):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4 # 595.27 x 841.89 pt
    
    # 1. Başlık Alanı
    c.setFont("Arial-Bold", 12)
    c.drawCentredString(width / 2.0, height - 50, "ŞÜPHELİ İFADE TUTANAĞI")
    
    # 2. Kimlik Bilgileri Tablosu
    start_y = height - 90
    line_spacing = 14
    colon_x = 215
    val_x = 225
    curr_y = start_y
    
    fields = [
        ("T.C. Kimlik Numarası", "12763143108"),
        ("Adı ve Soyadı", "Cafer GÜDER"),
        ("Vekili", "Yok"),
        ("Baba ve Ana Adı", "Murat / Günay"),
        ("Doğum Yeri ve Tarihi", "Eskişehir - 01/01/2000"),
        ("Nüfusa Kayıtlı Olduğu Yer", "Eskişehir / Tepebaşı"),
        ("İkametgah Adresi", "Kumlubel Mah. Kahraman Sk. Mina Merve Apt. No:11 İç Kapı No:1 Tepebaşı / ESKİŞEHİR"),
        ("İş Yeri Adresi", "Tepebaşı Belediyesi - ESKİŞEHİR"),
        ("Varsa Telefonu (Ev-İş-Cep-İrtibat)", "0535 258 35 02"),
        ("Mesleği, Ekonomik Durumu", "Belediye Personeli, Düzenli Sabit Gelirli"),
        ("Medeni Hali, Çocuk Sayısı", "Bekar, Çocuksuz"),
        ("İfadenin Alındığı Yer", "Tepebaşı Polis Merkezi Amirliği"),
    ]
    
    for label, val in fields:
        c.setFont("Arial-Bold", 8.5)
        c.drawString(45, curr_y, label)
        c.drawString(colon_x, curr_y, ":")
        c.setFont("Arial", 8.5)
        
        # Uzun adres kontrolü
        if len(val) > 60:
            words = val.split(" ")
            line1, line2 = "", ""
            for w in words:
                if len(line1 + " " + w) < 58:
                    line1 += (" " if line1 else "") + w
                else:
                    line2 += (" " if line2 else "") + w
            c.drawString(val_x, curr_y, line1)
            curr_y -= 11.5
            c.drawString(val_x, curr_y, line2)
        else:
            c.drawString(val_x, curr_y, val)
        curr_y -= line_spacing
        
    curr_y -= 8
    
    # 3. Yasal Uyarı Bloğu (Şablondaki Matbu Metin)
    style_justified = ParagraphStyle(
        name='JustifiedText',
        fontName='Arial',
        fontSize=8.5,
        leading=12,
        alignment=4 # Justify
    )
    
    def draw_para(p_text, y_pos):
        p = Paragraph(p_text, style_justified)
        w, h = p.wrap(width - 90, 300)
        p.drawOn(c, 45, y_pos - h)
        return y_pos - h
        
    matbu_uyari = (
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;İfade verene yüklenen suç anlatıldı, "
        "müdafii seçme hakkının bulunduğu ve onun hukuki yardımından yararlanabileceği, "
        "müdafiin ifade alma sırasında hazır bulunabileceği, isnat edilen suç hakkında açıklamada bulunmamasının "
        "kanuni hakkı olduğu, şüpheden kurtulması için somut delillerin toplanmasını isteyebileceği kendisine "
        "hatırlatılıp açıklandı."
    )
    curr_y = draw_para(matbu_uyari, curr_y)
    curr_y -= 8
    
    matbu_secim = (
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Hak ve imkanlarımı anladım, "
        "<b>müdafii istemiyorum, savunmamı kendim yapacağım</b> dedi."
    )
    curr_y = draw_para(matbu_secim, curr_y)
    curr_y -= 10
    
    c.setFont("Arial-Bold", 8.5)
    c.drawString(45, curr_y, "        Şüpheliden soruşturma konusu olayı anlatması istendi. Şüpheli cevaben;")
    curr_y -= 13
    
    # 4. Şüphelinin Esas Savunması (Tam sığacak, delil toplatma talepli, aklayıcı kurgu)
    ifade_metni = (
        "\"Üzerime atılı isnadı anladım. Ben Tepebaşı Belediyesi bünyesinde düzenli işi, sabit geliri ve sabıkasız "
        "geçmişi olan bir personelim. 03.10.2026 günü saat 01:40 sıralarında sevk ve idaremdeki 26 SR 471 plakalı araçla "
        "seyir halindeyken polis uygulama noktasına intikal ettim. Görevli memurların yönlendirmesiyle aracı kontrol alanına aldım. "
        "Uygulanan alkol ve teknik kontrollerde emniyet güçlerine her türlü kolaylığı sağladım.<br/><br/>"
        "Araç içerisinde yapılan arama sonucunda alüminyum folyo içine sarılı vaziyette metamfetamin olduğu bildirilen "
        "madde ve bir adet aparat ele geçirildiği tarafıma beyan edilmiştir. <b>Bahse konu madde ve aparat kesinlikle şahsıma ait DEĞİLDİR.</b> "
        "Söz konusu araç münhasıran benim kullanımımda olan bir araç olmayıp; gün içerisinde ailem, mesai arkadaşlarım ve yakın çevrem "
        "tarafından da sıklıkla kullanılan, zaman zaman emanet olarak verilen bir araçtır. Aracın görünmeyen bir noktasına bu maddelerin "
        "kim tarafından, ne zaman bırakıldığını veya düşürüldüğünü kesinlikle bilmiyorum; benim bilgi, irade ve hakimiyet alanım dışındadır.<br/><br/>"
        "Şahsımın uyuşturucu madde kullanmak, taşımak, bulundurmak veya ticaretini yapmak gibi hiçbir yasadışı eylem veya kastı olamaz. "
        "Suçsuzluğumun somut teknik delillerle sübuta ermesi amacıyla; ele geçirilen <b>folyo, ambalaj ve aparat üzerinden parmak izi ve "
        "biyolojik DNA (svap) incelemesi yapılmasını</b>, şahsımla mukayese edilmesini ve alınacak kan/idrar tahlillerimin dosyaya "
        "kazandırılmasını talep ediyorum. Sabit ikamet ve kamu işi sahibiyim, kaçma şüphem yoktur. Suçlamayı kabul etmiyorum, bihakkın serbest "
        "bırakılmamı talep ederim.\" dedi."
    )
    curr_y = draw_para(ifade_metni, curr_y)
    curr_y -= 12
    
    # 5. Kapanış Metni
    kapanis = (
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Konu hakkında söylemek istediklerinin bundan ibaret "
        "olduğunu belirtmesi üzerine işbu savunma zaptı bulunanların huzurunda imzalandı. 03/10/2026"
    )
    curr_y = draw_para(kapanis, curr_y)
    
    # 6. İmza Bloğu (İfade Alan Polis Memurları ve Şüpheli)
    sig_y = 95
    c.setFont("Arial-Bold", 8.5)
    c.drawCentredString(105, sig_y + 12, "İFADE ALAN POLİS MEMURU")
    c.setFont("Arial", 8.5)
    c.drawCentredString(105, sig_y - 2, "Mehmet SÖNMEZ")
    c.drawCentredString(105, sig_y - 16, "(İmza)")
    
    c.setFont("Arial-Bold", 8.5)
    c.drawCentredString(width / 2.0, sig_y + 12, "İFADE ALAN POLİS MEMURU")
    c.setFont("Arial", 8.5)
    c.drawCentredString(width / 2.0, sig_y - 2, "Ali YILDIRIM")
    c.drawCentredString(width / 2.0, sig_y - 16, "(İmza)")
    
    c.setFont("Arial-Bold", 8.5)
    c.drawCentredString(width - 105, sig_y + 12, "ŞÜPHELİ")
    c.setFont("Arial", 8.5)
    c.drawCentredString(width - 105, sig_y - 2, "Cafer GÜDER")
    c.drawCentredString(width - 105, sig_y - 16, "(İmza)")
    
    c.save()
    print("PDF oluşturuldu:", output_path)

if __name__ == "__main__":
    desktop_pdf = os.path.expanduser("~\\Desktop\\Supheli_Ifade_Tutanagi_Cafer_Guder.pdf")
    workspace_pdf = os.path.abspath("Supheli_Ifade_Tutanagi_Cafer_Guder.pdf")
    generate_tutanak(desktop_pdf)
    generate_tutanak(workspace_pdf)

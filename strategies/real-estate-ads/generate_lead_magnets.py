from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm

OUT = Path(__file__).parent / "public" / "assets"
OUT.mkdir(parents=True, exist_ok=True)
NAVY=colors.HexColor('#0E2742'); GREEN=colors.HexColor('#197447'); GOLD=colors.HexColor('#C3A15C')
LINE=colors.HexColor('#D7DEE7'); TEXT=colors.HexColor('#1D2939'); MUTED=colors.HexColor('#667085'); WHITE=colors.white
S=getSampleStyleSheet()
S.add(ParagraphStyle(name='F1Title',parent=S['Title'],fontName='Helvetica-Bold',fontSize=28,leading=33,textColor=WHITE,spaceAfter=12))
S.add(ParagraphStyle(name='F1Sub',parent=S['Normal'],fontName='Helvetica',fontSize=12,leading=18,textColor=colors.HexColor('#D8E1EA')))
S.add(ParagraphStyle(name='H1F1',parent=S['Heading1'],fontName='Helvetica-Bold',fontSize=19,leading=23,textColor=NAVY,spaceBefore=4,spaceAfter=10))
S.add(ParagraphStyle(name='BodyF1',parent=S['BodyText'],fontName='Helvetica',fontSize=10.2,leading=15.2,textColor=TEXT,spaceAfter=7))
S.add(ParagraphStyle(name='CalloutF1',parent=S['BodyText'],fontName='Helvetica-Bold',fontSize=10.2,leading=15,textColor=NAVY,backColor=colors.HexColor('#ECFDF3'),borderColor=colors.HexColor('#B7E7C7'),borderWidth=.7,borderPadding=8,spaceBefore=6,spaceAfter=10))
S.add(ParagraphStyle(name='NumF1',parent=S['BodyText'],fontName='Helvetica-Bold',fontSize=12.5,leading=16,textColor=GOLD,spaceAfter=3))

def footer(canvas,doc):
    canvas.saveState(); w,h=A4
    canvas.setStrokeColor(GOLD); canvas.setLineWidth(1.2); canvas.line(18*mm,h-13*mm,w-18*mm,h-13*mm)
    canvas.setFont('Helvetica-Bold',8); canvas.setFillColor(NAVY); canvas.drawString(18*mm,h-10*mm,'F1 IMMOBILIARE')
    canvas.setFont('Helvetica',7.5); canvas.setFillColor(MUTED); canvas.drawString(18*mm,9*mm,'Materiale informativo. Verificare sempre documenti, condizioni e professionisti coinvolti.')
    canvas.drawRightString(w-18*mm,9*mm,f'Pag. {doc.page}'); canvas.restoreState()

def cover(story,title,subtitle,kicker):
    data=[[Paragraph(kicker.upper(),ParagraphStyle('k',fontName='Helvetica-Bold',fontSize=9,textColor=GOLD)), ''],[Paragraph(title,S['F1Title']),''],[Paragraph(subtitle,S['F1Sub']),'']]
    t=Table(data,colWidths=[150*mm,20*mm],rowHeights=[14*mm,45*mm,30*mm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),NAVY),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),16),('RIGHTPADDING',(0,0),(-1,-1),16),('SPAN',(0,0),(1,0)),('SPAN',(0,1),(1,1)),('SPAN',(0,2),(1,2)),('LINEBELOW',(0,0),(-1,0),2,GOLD)]))
    story += [Spacer(1,15*mm),t,Spacer(1,12*mm),Paragraph('Come usare questo materiale',S['H1F1']),Paragraph('Usalo per organizzare domande, documenti e priorita prima di una proposta. Non sostituisce notaio, tecnico, banca o agente abilitato.',S['BodyF1']),Paragraph('Prima si chiariscono budget, documenti e priorita; poi si visita.',S['CalloutF1']),PageBreak()]

def checklist_table(items):
    rows=[[Paragraph('□',S['BodyF1']),Paragraph(x,S['BodyF1'])] for x in items]
    t=Table(rows,colWidths=[9*mm,158*mm]); t.setStyle(TableStyle([('BOX',(0,0),(-1,-1),.5,LINE),('INNERGRID',(0,0),(-1,-1),.25,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)])); return t

def guide():
    p=OUT/'F1_Guida_Acquisto_Casa_2026.pdf'; d=SimpleDocTemplate(str(p),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=18*mm,bottomMargin=18*mm); st=[]
    cover(st,'Guida pratica all\'acquisto casa 2026','10 errori da evitare prima della proposta, con controlli concreti su budget, documenti, mutuo e decisione.','Lead magnet acquirenti')
    items=[
    ('Partire dal prezzo e non dal budget reale','Definisci liquidita, rata sostenibile, spese notarili, imposte, eventuale mediazione, trasloco e primi lavori.'),
    ('Visitare senza priorita','Scrivi requisiti indispensabili, desiderabili e criteri di esclusione prima di iniziare le visite.'),
    ('Confondere metri commerciali e spazio utile','Confronta superficie commerciale, distribuzione, pertinenze e spazio realmente fruibile.'),
    ('Ignorare condominio e costi ricorrenti','Chiedi spese ordinarie, lavori straordinari, stato delle parti comuni e riscaldamento.'),
    ('Rimandare il mutuo','Se serve finanziamento, fai prima una verifica di sostenibilita e documenti reddituali.'),
    ('Firmare senza capire tempi e condizioni','Prezzo, caparra, acconti, rogito, consegna e condizioni devono essere chiari prima della firma.'),
    ('Sottovalutare la verifica documentale','Titolarita, catasto, urbanistica, vincoli, ipoteche e APE richiedono verifiche professionali.'),
    ('Valutare solo l\'interno','Esposizione, rumore, parcheggio, collegamenti, servizi e manutenzione del fabbricato contano.'),
    ('Farsi guidare dall\'urgenza artificiale','Chiedi scadenze reali, modalita di proposta e documenti disponibili.'),
    ('Non preparare un piano B','Definisci prima soglia massima di spesa, condizioni non negoziabili e cosa ti farebbe rinunciare.')]
    for i,(title,body) in enumerate(items,1):
        st += [Paragraph(f'{i:02d}',S['NumF1']),Paragraph(title,S['H1F1']),Paragraph(body,S['BodyF1']),checklist_table(['Ho verificato questo punto','So chi deve fornire il documento o la risposta']),Spacer(1,5*mm)]
        if i in (3,6,8): st.append(PageBreak())
    st += [PageBreak(),Paragraph('Prima della proposta',S['H1F1']),checklist_table(['Budget massimo complessivo definito','Mutuo/pre-valutazione impostata se necessaria','Spese condominiali e lavori straordinari verificati','Documenti essenziali disponibili o da reperire','Caparra, acconti, rogito e consegna chiari','Condizioni non negoziabili definite']),Spacer(1,7*mm),Paragraph('Una ricerca qualificata parte dai criteri, non dal numero di annunci guardati.',S['CalloutF1'])]
    d.build(st,onFirstPage=footer,onLaterPages=footer)

def first_home():
    p=OUT/'F1_Checklist_Prima_Casa_2026.pdf'; d=SimpleDocTemplate(str(p),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=18*mm,bottomMargin=18*mm); st=[]
    cover(st,'Checklist Prima Casa 2026','Controlli, costi e documenti da organizzare prima della proposta e prima del rogito.','Percorso operativo')
    blocks=[
    ('1. PRIMA DI CERCARE',['Definisci budget massimo comprensivo delle spese','Calcola liquidita disponibile per caparra/acconti','Stima rata sostenibile e margine mensile','Prepara documenti reddituali se serve mutuo','Definisci requisiti e zone compatibili']),
    ('2. QUANDO TROVI UN IMMOBILE',['Chiedi planimetria e dati essenziali','Verifica prezzo, pertinenze e beni inclusi','Chiedi spese condominiali e lavori straordinari','Controlla esposizione, rumore, accessibilita e parcheggio','Visita la zona in orari diversi']),
    ('3. PRIMA DELLA PROPOSTA',['Chiarisci caparra, scadenza proposta, rogito e consegna','Valuta correttamente la tutela legata al mutuo con professionisti','Verifica quali documenti sono disponibili e quali mancano','Non lasciare accordi economici importanti solo a voce']),
    ('4. DOCUMENTI DA FAR VERIFICARE',['Titolo/provenienza','Visura e planimetria catastale','Documentazione urbanistica disponibile','APE','Eventuali ipoteche, vincoli o gravami','Regolamento e situazione condominiale quando applicabile']),
    ('5. PRIMA DEL ROGITO',['Conferma saldo prezzo e modalita di pagamento','Conferma consegna chiavi e liberazione immobile','Organizza utenze e assicurazione se necessaria','Mantieni un fondo per spese iniziali, arredi e lavori'])]
    for i,(h,it) in enumerate(blocks):
        st += [Paragraph(h,S['H1F1']),checklist_table(it),Spacer(1,7*mm)]
        if i in (1,3): st.append(PageBreak())
    st += [Paragraph('Questa checklist e uno strumento organizzativo. Le verifiche tecniche, fiscali, bancarie e notarili devono essere svolte dai professionisti competenti.',S['CalloutF1'])]
    d.build(st,onFirstPage=footer,onLaterPages=footer)

if __name__=='__main__':
    guide(); first_home(); print(OUT)

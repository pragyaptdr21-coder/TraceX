from fpdf import FPDF
import io

class TraceXPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'TraceX Investigation Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def export_pdf(title: str, content: str) -> bytes:
    pdf = TraceXPDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, title, 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 11)
    
    # Simple multi_cell for content, replacing unsupported characters if needed
    safe_content = content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, safe_content)
    
    return pdf.output(dest='S').encode('latin-1')

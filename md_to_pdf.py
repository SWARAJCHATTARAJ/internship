


from markdown_pdf import Section, MarkdownPdf

pdf = MarkdownPdf(toc_level=2)

with open("Project_Documentation.md", "r", encoding="utf-8") as f:
    text = f.read()

pdf.add_section(Section(text))
pdf.save("Project_Documentation.pdf")
print("PDF generated successfully!")

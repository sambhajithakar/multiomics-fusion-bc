const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, HeadingLevel,
  Table, TableRow, TableCell, WidthType, BorderStyle, Footer, PageNumber,
} = require("docx");

const FONT = "Calibri";
const BODY_SIZE = 22; // 11pt
const SMALL_SIZE = 18;

function p(text, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.LEFT,
    spacing: { after: opts.after ?? 200, line: 276 },
    children: [new TextRun({
      text, font: FONT, size: opts.size || BODY_SIZE, bold: !!opts.bold, italics: !!opts.italics,
    })],
  });
}

function heading(text, level = HeadingLevel.HEADING_1) {
  return new Paragraph({
    heading: level,
    spacing: { before: 300, after: 200 },
    children: [new TextRun({ text, font: FONT, bold: true, size: 26, color: "1F3864" })],
  });
}

function cell(text, opts = {}) {
  return new TableCell({
    width: opts.width ? { size: opts.width, type: WidthType.PERCENTAGE } : undefined,
    shading: opts.header ? { fill: "1F3864" } : undefined,
    children: [new Paragraph({
      children: [new TextRun({
        text, font: FONT, size: SMALL_SIZE + 2, bold: !!opts.header,
        color: opts.header ? "FFFFFF" : "000000",
      })],
    })],
  });
}

function row(cells) {
  return new TableRow({ children: cells, cantSplit: true });
}

const reviewers = [
  ["Prof. Lana X. Garmire", "University of Alabama at Birmingham, Dept. of Biomedical Informatics and Data Science, USA (previously University of Michigan)", "Deep learning-based multi-omics integration for cancer survival/subtype prediction", "lgarmire@uab.edu", "Not publicly listed"],
  ["Prof. Anna Goldenberg", "University of Toronto / SickKids Research Institute, Dept. of Laboratory Medicine and Pathobiology, Canada", "Similarity network fusion; multi-omics data integration methods", "anna.goldenberg@utoronto.ca", "Not publicly listed"],
  ["Prof. Christina Curtis", "Stanford University, Dept. of Medicine (Oncology) and Genetics, USA", "METABRIC; breast cancer genomics and AI in cancer genomics", "Not publicly listed (Stanford Profiles contact form only)", "Not publicly listed"],
  ["Prof. Ron Shamir", "Tel Aviv University, Blavatnik School of Computer Science, Israel", "Multi-omic and multi-view clustering benchmarking for cancer subtypes", "rshamir@tau.ac.il", "Not publicly listed"],
  ["Prof. Martin Ester", "Simon Fraser University, School of Computing Science, Canada", "Deep neural network late integration of multi-omics data (MOLI) for oncology prediction tasks", "ester@sfu.ca", "Not publicly listed"],
  ["Prof. Marc Ladanyi", "Memorial Sloan Kettering Cancer Center, Dept. of Pathology and Laboratory Medicine, USA", "Integrative genomic clustering (iCluster); cancer molecular pathology", "Not publicly listed", "Not publicly listed"],
];

const children = [];

children.push(new Paragraph({
  spacing: { after: 100 },
  children: [new TextRun({
    text: "Suggested Reviewers",
    font: FONT, size: 32, bold: true, color: "1F3864",
  })],
}));

children.push(p(
  "Manuscript: “Deep Multi-Omics Fusion for Breast Cancer Molecular Subtyping and Recurrence Risk Prediction: A Schema-Matched Synthetic Proof-of-Concept” — submitted to Artificial Intelligence in Medicine.",
  { italics: true, after: 300 }
));

children.push(p(
  "The following researchers were identified based on directly relevant, publicly documented expertise in multi-omics data integration, deep learning-based cancer subtyping, and breast cancer genomics; several of their publications are cited in this manuscript. Emails below were taken directly from each researcher's official institutional/lab page where published; where no personal email or phone number is publicly listed, this is stated explicitly rather than guessed. Verify all details are still current and screen each name against the journal's conflict-of-interest criteria (e.g., no recent co-authorship, shared institution, or mentorship relationship with any author) before final selection.",
  { after: 300 }
));

const table = new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  rows: [
    row([
      cell("Name", { header: true, width: 16 }),
      cell("Affiliation", { header: true, width: 26 }),
      cell("Relevant expertise", { header: true, width: 22 }),
      cell("Email", { header: true, width: 18 }),
      cell("Phone", { header: true, width: 18 }),
    ]),
    ...reviewers.map(([name, aff, exp, email, phone]) => row([
      cell(name, { width: 16 }),
      cell(aff, { width: 26 }),
      cell(exp, { width: 22 }),
      cell(email, { width: 18 }),
      cell(phone, { width: 18 }),
    ])),
  ],
});
children.push(table);

children.push(new Paragraph({ spacing: { before: 300 }, children: [] }));

children.push(heading("Notes", HeadingLevel.HEADING_2));
[
  "Most journal submission portals (including Elsevier's Editorial Manager, typically used by Artificial Intelligence in Medicine) cap suggested reviewers at 3–5 — confirm the exact limit on the submission form and select accordingly; you do not need to submit all six.",
  "Individual academics rarely publish a direct personal phone number; where marked “Not publicly listed,” no direct contact was found on the researcher's own institutional or lab page — only third-party data-broker sites (which are frequently inaccurate) claim to have it, so none is given here.",
  "Prof. Garmire's group page listed a University of Alabama at Birmingham address at the time this list was generated, distinct from her earlier University of Michigan affiliation cited in the manuscript's reference list — both are noted here; re-verify her current institution before submission.",
  "An “excluded reviewers” list may also be submitted if there is anyone with a genuine conflict of interest.",
  "All information here reflects a check performed on the date of this document's generation; re-verify immediately before submission in case of role or institutional changes.",
].forEach(t => children.push(new Paragraph({
  bullet: { level: 0 },
  spacing: { after: 150 },
  children: [new TextRun({ text: t, font: FONT, size: BODY_SIZE })],
})));

const doc = new Document({
  sections: [{
    properties: {
      page: {
        size: { width: 15840, height: 12240, orientation: "landscape" },
        margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Page ", font: FONT, size: 16, color: "808080" }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "808080" })],
        })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("manuscript/reviewer_list.docx", buf);
  console.log("wrote manuscript/reviewer_list.docx", buf.length, "bytes");
});

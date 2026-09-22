const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, HeadingLevel,
} = require("docx");

const FONT = "Calibri";
const BODY_SIZE = 22; // 11pt

function p(text, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.LEFT,
    spacing: { after: opts.after ?? 200, line: 276 },
    children: [new TextRun({
      text, font: FONT, size: opts.size || BODY_SIZE, bold: !!opts.bold, italics: !!opts.italics,
    })],
  });
}

const today = "September 22, 2026";

const children = [];

children.push(p(today, { after: 300 }));

children.push(p("The Editor-in-Chief", { after: 0 }));
children.push(p("Artificial Intelligence in Medicine", { after: 0 }));
children.push(p("Elsevier", { after: 400 }));

children.push(p("Dear Editor,", { after: 300 }));

children.push(p(
  "We are pleased to submit our original research article entitled “Deep Multi-Omics Fusion for Breast Cancer Molecular Subtyping and Recurrence Risk Prediction: A Schema-Matched Synthetic Proof-of-Concept” for consideration for publication in Artificial Intelligence in Medicine.",
  { after: 250 }
));

children.push(p(
  "Breast cancer molecular subtyping and recurrence-risk assessment still rely heavily on PAM50 gene-expression profiling, even though real tumors carry genomic, epigenetic and proteomic alterations that a single expression panel cannot capture. Our manuscript presents a deep multi-branch fusion architecture that integrates genomic (mutation/amplification), transcriptomic (90-gene panel including the full PAM50 set), proteomic (45-antibody reverse-phase array-style panel) and methylation (35-probe promoter panel) data through per-omics neural sub-networks feeding a fusion head, and applies it to two tasks: four-class molecular subtype classification and five-year recurrence-risk prediction intended to test whether multi-omics fusion can improve on PAM50 subtype alone.",
  { after: 250 }
));

children.push(p(
  "As a mechanical validation of this framework ahead of its application to real paired multi-omics data, we constructed a synthetic, schema-matched cohort (n = 520) built to mirror the structure of TCGA-BRCA and METABRIC, with a checkable ground truth. The fusion model matched PAM50-expression-based subtype classification (macro-AUC = 0.992 vs 0.999) while every individual omics layer, including genomics alone, classified subtype well above chance (AUC 0.823-0.989), and bootstrap analysis identified a reproducible 16-feature multi-omics signature whose members correlated with expected ER, HER2, proliferation and basal biology in the predicted direction. For five-year recurrence prediction, however, multi-omics fusion did not significantly outperform a PAM50-subtype-plus-clinical baseline in this cohort (ΔAUC = -0.003, Wilcoxon p = 0.42) -- a negative result we report transparently and use to identify a specific, checkable limitation in how subtype-independent genomic risk was represented in our synthetic design, directly informing what a real-data application to TCGA-BRCA and METABRIC would need to test the “beyond PAM50” hypothesis properly. We believe this combination of a working multi-omics fusion architecture, an honestly reported non-significant finding, and a clear diagnosis of why, is well matched to the scope and readership of Artificial Intelligence in Medicine.",
  { after: 250 }
));

children.push(p(
  "This manuscript is original, has not been published previously, and is not under consideration for publication elsewhere, in whole or in part. All authors have approved the manuscript and agree with its submission to Artificial Intelligence in Medicine. The authors declare no conflicts of interest. Complete code to reproduce every reported number and figure is publicly available (see Code availability), and the manuscript includes a Declaration of generative AI use disclosing the tools used during pipeline development and drafting.",
  { after: 250 }
));

children.push(p(
  "We hope you find this work suitable for review and look forward to your response.",
  { after: 400 }
));

children.push(p("Sincerely, on behalf of all authors (Sambhaji Balaso Thakar, Pradnya Sambhaji Thakar, Anil Sangle, and Dokyun Na),", { after: 300 }));

children.push(p("Prof. Dokyun Na, Ph.D.", { bold: true, after: 0 }));
children.push(p("Professor, School of Integrative Engineering", { after: 0 }));
children.push(p("Chung-Ang University, 84 Heukseok-ro, Dongjak-gu, Seoul, Republic of Korea", { after: 0 }));
children.push(p("Email: blisszen@lile.cau.ac.kr", { after: 0 }));

const doc = new Document({
  sections: [{
    properties: { page: { margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("manuscript/cover_letter.docx", buf);
  console.log("wrote manuscript/cover_letter.docx", buf.length, "bytes");
});

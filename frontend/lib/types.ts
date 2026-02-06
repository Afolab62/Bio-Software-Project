// Core types for the Direct Evolution Monitoring Portal

export interface User {
  id: string;
  email: string;
  passwordHash: string;
  createdAt: Date;
}

export interface UniProtProtein {
  accession: string;
  name: string;
  organism: string;
  sequence: string;
  length: number;
  features: UniProtFeature[];
}

export interface UniProtFeature {
  type: string;
  description: string;
  location: {
    start: number;
    end: number;
  };
}

export interface Experiment {
  id: string;
  userId: string;
  name: string;
  proteinAccession: string;
  proteinName?: string | null;
  protein: UniProtProtein | null;
  wtProteinSequence?: string;
  proteinFeatures?: any;
  plasmidSequence: string;
  plasmidName: string;
  validationStatus: "pending" | "valid" | "invalid";
  validationMessage: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface VariantData {
  id: string;
  experimentId: string;
  plasmidVariantIndex: number;
  parentPlasmidVariant: number | null;
  generation: number;
  assembledDNASequence: string;
  proteinSequence: string;
  dnaYield: number;
  proteinYield: number;
  fluorescence: number;
  activityScore: number;
  isControl: boolean;
  mutations: Mutation[];
  qcStatus: "passed" | "failed";
  qcMessage: string;
  metadata: Record<string, unknown>;
}

export interface Mutation {
  position: number;
  wildType: string;
  mutant: string;
  type: "synonymous" | "non-synonymous";
  generation: number;
}

export interface ParseResult {
  success: boolean;
  variants: VariantData[];
  errors: ParseError[];
  warnings: string[];
}

export interface ParseError {
  row: number;
  field: string;
  message: string;
}

export interface AnalysisResult {
  topPerformers: VariantData[];
  generationStats: GenerationStats[];
  totalVariants: number;
  passedQC: number;
  failedQC: number;
}

export interface GenerationStats {
  generation: number;
  count: number;
  meanActivity: number;
  medianActivity: number;
  minActivity: number;
  maxActivity: number;
  stdDev: number;
}

// Codon table for DNA to Protein translation
export const CODON_TABLE: Record<string, string> = {
  TTT: "F",
  TTC: "F",
  TTA: "L",
  TTG: "L",
  TCT: "S",
  TCC: "S",
  TCA: "S",
  TCG: "S",
  TAT: "Y",
  TAC: "Y",
  TAA: "*",
  TAG: "*",
  TGT: "C",
  TGC: "C",
  TGA: "*",
  TGG: "W",
  CTT: "L",
  CTC: "L",
  CTA: "L",
  CTG: "L",
  CCT: "P",
  CCC: "P",
  CCA: "P",
  CCG: "P",
  CAT: "H",
  CAC: "H",
  CAA: "Q",
  CAG: "Q",
  CGT: "R",
  CGC: "R",
  CGA: "R",
  CGG: "R",
  ATT: "I",
  ATC: "I",
  ATA: "I",
  ATG: "M",
  ACT: "T",
  ACC: "T",
  ACA: "T",
  ACG: "T",
  AAT: "N",
  AAC: "N",
  AAA: "K",
  AAG: "K",
  AGT: "S",
  AGC: "S",
  AGA: "R",
  AGG: "R",
  GTT: "V",
  GTC: "V",
  GTA: "V",
  GTG: "V",
  GCT: "A",
  GCC: "A",
  GCA: "A",
  GCG: "A",
  GAT: "D",
  GAC: "D",
  GAA: "E",
  GAG: "E",
  GGT: "G",
  GGC: "G",
  GGA: "G",
  GGG: "G",
};

// Reverse complement for handling circular DNA
export function reverseComplement(dna: string): string {
  const complement: Record<string, string> = {
    A: "T",
    T: "A",
    G: "C",
    C: "G",
    a: "t",
    t: "a",
    g: "c",
    c: "g",
  };
  return dna
    .split("")
    .reverse()
    .map((base) => complement[base] || base)
    .join("");
}

// Translate DNA to protein
export function translateDNA(dna: string): string {
  const protein: string[] = [];
  const cleanDNA = dna.toUpperCase().replace(/[^ATGC]/g, "");

  for (let i = 0; i < cleanDNA.length - 2; i += 3) {
    const codon = cleanDNA.substring(i, i + 3);
    const aa = CODON_TABLE[codon];
    if (aa === "*") break; // Stop codon
    if (aa) protein.push(aa);
  }

  return protein.join("");
}

// Find all ORFs in a sequence (handles circular DNA)
export function findORFs(
  dna: string,
  minLength: number = 100,
): Array<{ start: number; end: number; protein: string; frame: number }> {
  const orfs: Array<{
    start: number;
    end: number;
    protein: string;
    frame: number;
  }> = [];
  const cleanDNA = dna.toUpperCase().replace(/[^ATGC]/g, "");

  // For circular DNA, duplicate the sequence to find ORFs that wrap around
  const extendedDNA = cleanDNA + cleanDNA.substring(0, cleanDNA.length);

  // Check all 6 reading frames (3 forward, 3 reverse)
  for (let frame = 0; frame < 3; frame++) {
    // Forward strand
    let inORF = false;
    let orfStart = 0;
    let protein = "";

    for (let i = frame; i < extendedDNA.length - 2; i += 3) {
      // Only process up to 2x original length for circular handling
      if (i >= cleanDNA.length * 2) break;

      const codon = extendedDNA.substring(i, i + 3);
      const aa = CODON_TABLE[codon];

      if (!inORF && codon === "ATG") {
        inORF = true;
        orfStart = i % cleanDNA.length;
        protein = "M";
      } else if (inORF) {
        if (aa === "*" || !aa) {
          if (protein.length >= minLength) {
            orfs.push({
              start: orfStart,
              end: i % cleanDNA.length,
              protein,
              frame,
            });
          }
          inORF = false;
          protein = "";
        } else {
          protein += aa;
        }
      }
    }
  }

  // Also check reverse complement
  const revComp = reverseComplement(cleanDNA);
  const extendedRevComp = revComp + revComp.substring(0, revComp.length);

  for (let frame = 0; frame < 3; frame++) {
    let inORF = false;
    let orfStart = 0;
    let protein = "";

    for (let i = frame; i < extendedRevComp.length - 2; i += 3) {
      if (i >= revComp.length * 2) break;

      const codon = extendedRevComp.substring(i, i + 3);
      const aa = CODON_TABLE[codon];

      if (!inORF && codon === "ATG") {
        inORF = true;
        orfStart = i % revComp.length;
        protein = "M";
      } else if (inORF) {
        if (aa === "*" || !aa) {
          if (protein.length >= minLength) {
            orfs.push({
              start: orfStart,
              end: i % revComp.length,
              protein,
              frame: -(frame + 1),
            });
          }
          inORF = false;
          protein = "";
        } else {
          protein += aa;
        }
      }
    }
  }

  return orfs.sort((a, b) => b.protein.length - a.protein.length);
}

// Calculate sequence similarity (for protein matching)
export function sequenceSimilarity(seq1: string, seq2: string): number {
  if (seq1.length === 0 || seq2.length === 0) return 0;

  const shorter = seq1.length < seq2.length ? seq1 : seq2;
  const longer = seq1.length < seq2.length ? seq2 : seq1;

  let matches = 0;
  for (let i = 0; i < shorter.length; i++) {
    if (shorter[i] === longer[i]) matches++;
  }

  return matches / longer.length;
}

import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "100";
    const offset = searchParams.get("offset") || "0";

    // Forward cookies from browser to Flask backend
    const cookieHeader = request.headers.get("cookie");

    const response = await fetch(
      `${BACKEND_URL}/api/experiments?limit=${limit}&offset=${offset}`,
      {
        method: "GET",
        headers: cookieHeader ? { Cookie: cookieHeader } : {},
        credentials: "include",
      },
    );

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to connect to server" },
      { status: 500 },
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Forward cookies from browser to Flask backend
    const cookieHeader = request.headers.get("cookie");

    const response = await fetch(`${BACKEND_URL}/api/experiments`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(cookieHeader ? { Cookie: cookieHeader } : {}),
      },
      credentials: "include",
      body: JSON.stringify(body),
    });

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to connect to server" },
      { status: 500 },
    );
  }
}

function cleanFastaSequence(fasta: string): string {
  // Remove FASTA header lines and whitespace
  return fasta
    .split("\n")
    .filter((line) => !line.startsWith(">"))
    .join("")
    .replace(/\s/g, "")
    .toUpperCase();
}

function validatePlasmid(
  plasmidSequence: string,
  proteinSequence: string,
): {
  isValid: boolean;
  message: string;
  similarity?: number;
  orfInfo?: { start: number; end: number; frame: number };
} {
  const cleanPlasmid = cleanFastaSequence(plasmidSequence);

  if (cleanPlasmid.length < 100) {
    return {
      isValid: false,
      message: "Plasmid sequence is too short (minimum 100 bp)",
    };
  }

  // Find all ORFs in the plasmid (handles circular DNA)
  const orfs = findORFs(cleanPlasmid, Math.floor(proteinSequence.length * 0.5));

  if (orfs.length === 0) {
    return {
      isValid: false,
      message:
        "No significant open reading frames found in the plasmid sequence",
    };
  }

  // Check each ORF for similarity to the target protein
  let bestMatch = { similarity: 0, orf: orfs[0] };

  for (const orf of orfs) {
    const similarity = sequenceSimilarity(orf.protein, proteinSequence);
    if (similarity > bestMatch.similarity) {
      bestMatch = { similarity, orf };
    }
  }

  // Require at least 70% similarity for validation
  if (bestMatch.similarity >= 0.7) {
    const frameDescription =
      bestMatch.orf.frame > 0
        ? `forward strand, frame ${bestMatch.orf.frame}`
        : `reverse strand, frame ${Math.abs(bestMatch.orf.frame)}`;

    return {
      isValid: true,
      message: `Protein coding sequence found with ${(bestMatch.similarity * 100).toFixed(1)}% identity (${frameDescription})`,
      similarity: bestMatch.similarity,
      orfInfo: {
        start: bestMatch.orf.start,
        end: bestMatch.orf.end,
        frame: bestMatch.orf.frame,
      },
    };
  }

  return {
    isValid: false,
    message: `Best match found has only ${(bestMatch.similarity * 100).toFixed(1)}% identity to the target protein (minimum 70% required)`,
    similarity: bestMatch.similarity,
  };
}

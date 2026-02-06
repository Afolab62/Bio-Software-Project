import { NextResponse } from 'next/server'
import type { UniProtProtein, UniProtFeature } from '@/lib/types'

export async function GET(
  request: Request,
  { params }: { params: Promise<{ accession: string }> }
) {
  const { accession } = await params

  if (!accession || accession.length < 4) {
    return NextResponse.json(
      { success: false, error: 'Invalid accession ID' },
      { status: 400 }
    )
  }

  try {
    // Fetch protein data from UniProt API
    const uniprotRes = await fetch(
      `https://rest.uniprot.org/uniprotkb/${accession}.json`,
      {
        headers: {
          'Accept': 'application/json',
        },
      }
    )

    if (!uniprotRes.ok) {
      if (uniprotRes.status === 404) {
        return NextResponse.json(
          { success: false, error: `Protein with accession "${accession}" not found in UniProt` },
          { status: 404 }
        )
      }
      throw new Error(`UniProt API error: ${uniprotRes.status}`)
    }

    const data = await uniprotRes.json()

    // Extract relevant information
    const protein: UniProtProtein = {
      accession: data.primaryAccession || accession,
      name: data.proteinDescription?.recommendedName?.fullName?.value || 
            data.proteinDescription?.submissionNames?.[0]?.fullName?.value ||
            'Unknown protein',
      organism: data.organism?.scientificName || 'Unknown organism',
      sequence: data.sequence?.value || '',
      length: data.sequence?.length || 0,
      features: extractFeatures(data.features || []),
    }

    return NextResponse.json({
      success: true,
      protein,
    })
  } catch (error) {
    console.error('UniProt API error:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch protein data from UniProt' },
      { status: 500 }
    )
  }
}

function extractFeatures(features: Array<{
  type: string
  description?: string
  location?: {
    start?: { value: number }
    end?: { value: number }
  }
}>): UniProtFeature[] {
  const relevantTypes = [
    'Domain', 'Region', 'Active site', 'Binding site', 
    'DNA binding', 'Metal binding', 'Site', 'Motif'
  ]

  return features
    .filter(f => relevantTypes.includes(f.type))
    .map(f => ({
      type: f.type,
      description: f.description || f.type,
      location: {
        start: f.location?.start?.value || 0,
        end: f.location?.end?.value || 0,
      },
    }))
    .slice(0, 20) // Limit to 20 features for display
}

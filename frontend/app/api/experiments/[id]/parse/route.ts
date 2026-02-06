import { NextResponse } from 'next/server'
import { store } from '@/lib/store'
import { translateDNA, findORFs, sequenceSimilarity, type VariantData, type Mutation } from '@/lib/types'

interface RawVariant {
  Plasmid_Variant_Index?: number
  plasmid_variant_index?: number
  Parent_Plasmid_Variant?: number | null
  parent_plasmid_variant?: number | null
  Generation?: number
  generation?: number
  Assembled_DNA_Sequence?: string
  assembled_dna_sequence?: string
  DNA_Yield?: number
  dna_yield?: number
  Protein_Yield?: number
  protein_yield?: number
  Fluorescence?: number
  fluorescence?: number
  Is_Control?: boolean
  is_control?: boolean
  [key: string]: unknown
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  
  try {
    const body = await request.json()
    const { data, format } = body

    const experiment = store.getExperiment(id)
    if (!experiment) {
      return NextResponse.json(
        { success: false, error: 'Experiment not found' },
        { status: 404 }
      )
    }

    if (!experiment.protein) {
      return NextResponse.json(
        { success: false, error: 'Experiment protein data is missing' },
        { status: 400 }
      )
    }

    // Parse the data based on format
    let rawVariants: RawVariant[]
    
    if (format === 'json') {
      rawVariants = typeof data === 'string' ? JSON.parse(data) : data
    } else if (format === 'tsv') {
      rawVariants = parseTSV(data)
    } else {
      return NextResponse.json(
        { success: false, error: 'Unsupported format. Use "json" or "tsv"' },
        { status: 400 }
      )
    }

    if (!Array.isArray(rawVariants) || rawVariants.length === 0) {
      return NextResponse.json(
        { success: false, error: 'No data found in the uploaded file' },
        { status: 400 }
      )
    }

    // Process variants with QC and analysis
    const { variants, errors, warnings } = processVariants(
      rawVariants, 
      id, 
      experiment.protein.sequence,
      experiment.plasmidSequence
    )

    // Store the processed variants
    store.setVariants(id, variants)

    // Update experiment status
    store.updateExperiment(id, {
      validationStatus: variants.length > 0 ? 'valid' : 'invalid',
    })

    return NextResponse.json({
      success: true,
      parsed: rawVariants.length,
      processed: variants.length,
      passedQC: variants.filter(v => v.qcStatus === 'passed').length,
      failedQC: variants.filter(v => v.qcStatus === 'failed').length,
      errors,
      warnings,
    })
  } catch (error) {
    console.error('Parse error:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to parse data file' },
      { status: 500 }
    )
  }
}

function parseTSV(data: string): RawVariant[] {
  const lines = data.trim().split('\n')
  if (lines.length < 2) return []

  const headers = lines[0].split('\t').map(h => h.trim())
  const variants: RawVariant[] = []

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split('\t')
    const variant: RawVariant = {}
    
    headers.forEach((header, idx) => {
      const value = values[idx]?.trim()
      
      // Convert numeric fields
      if (['Plasmid_Variant_Index', 'Parent_Plasmid_Variant', 'Generation'].includes(header)) {
        variant[header] = value ? parseInt(value, 10) : null
      } else if (['DNA_Yield', 'Protein_Yield', 'Fluorescence'].includes(header)) {
        variant[header] = value ? parseFloat(value) : 0
      } else if (['Is_Control'].includes(header)) {
        variant[header] = value?.toLowerCase() === 'true' || value === '1'
      } else {
        variant[header] = value
      }
    })
    
    variants.push(variant)
  }

  return variants
}

function processVariants(
  rawVariants: RawVariant[],
  experimentId: string,
  wtProteinSequence: string,
  plasmidSequence: string
): { variants: VariantData[], errors: Array<{row: number, field: string, message: string}>, warnings: string[] } {
  const variants: VariantData[] = []
  const errors: Array<{row: number, field: string, message: string}> = []
  const warnings: string[] = []

  // Get WT control data for normalization
  const controls = rawVariants.filter(v => 
    v.Is_Control || v.is_control || 
    (v.Generation === 0 || v.generation === 0)
  )

  let baselineDNA = 0
  let baselineProtein = 0
  
  if (controls.length > 0) {
    baselineDNA = controls.reduce((sum, c) => sum + (c.DNA_Yield || c.dna_yield || 0), 0) / controls.length
    baselineProtein = controls.reduce((sum, c) => sum + (c.Protein_Yield || c.protein_yield || 0), 0) / controls.length
  } else {
    warnings.push('No control samples found. Using global average for normalization.')
    baselineDNA = rawVariants.reduce((sum, v) => sum + (v.DNA_Yield || v.dna_yield || 0), 0) / rawVariants.length
    baselineProtein = rawVariants.reduce((sum, v) => sum + (v.Protein_Yield || v.protein_yield || 0), 0) / rawVariants.length
  }

  // Track variants by index for mutation tracking
  const variantsByIndex = new Map<number, { generation: number, mutations: Mutation[] }>()

  for (let i = 0; i < rawVariants.length; i++) {
    const raw = rawVariants[i]
    const rowNum = i + 2 // Account for header row and 1-indexing

    // Get values with case-insensitive fallback
    const plasmidIndex = raw.Plasmid_Variant_Index ?? raw.plasmid_variant_index
    const parentIndex = raw.Parent_Plasmid_Variant ?? raw.parent_plasmid_variant
    const generation = raw.Generation ?? raw.generation ?? 0
    const dnaSequence = raw.Assembled_DNA_Sequence ?? raw.assembled_dna_sequence ?? ''
    const dnaYield = raw.DNA_Yield ?? raw.dna_yield ?? 0
    const proteinYield = raw.Protein_Yield ?? raw.protein_yield ?? 0
    const fluorescence = raw.Fluorescence ?? raw.fluorescence ?? 0
    const isControl = raw.Is_Control ?? raw.is_control ?? false

    // QC: Check required fields
    let qcStatus: 'passed' | 'failed' = 'passed'
    let qcMessage = 'All checks passed'

    if (plasmidIndex === undefined || plasmidIndex === null) {
      errors.push({ row: rowNum, field: 'Plasmid_Variant_Index', message: 'Missing required field' })
      qcStatus = 'failed'
      qcMessage = 'Missing Plasmid_Variant_Index'
    }

    if (!dnaSequence) {
      errors.push({ row: rowNum, field: 'Assembled_DNA_Sequence', message: 'Missing DNA sequence' })
      qcStatus = 'failed'
      qcMessage = 'Missing DNA sequence'
    }

    // Translate DNA to protein and identify mutations
    let proteinSequence = ''
    let mutations: Mutation[] = []

    if (dnaSequence) {
      // Find the best ORF that matches the WT protein
      const orfs = findORFs(dnaSequence, 50)
      
      if (orfs.length > 0) {
        // Find the ORF most similar to WT protein
        let bestOrf = orfs[0]
        let bestSimilarity = 0
        
        for (const orf of orfs) {
          const sim = sequenceSimilarity(orf.protein, wtProteinSequence)
          if (sim > bestSimilarity) {
            bestSimilarity = sim
            bestOrf = orf
          }
        }
        
        proteinSequence = bestOrf.protein

        // Identify mutations compared to WT
        mutations = identifyMutations(wtProteinSequence, proteinSequence, generation, parentIndex, variantsByIndex)
      } else {
        // Direct translation if no ORF found
        proteinSequence = translateDNA(dnaSequence)
        if (proteinSequence.length < 50) {
          warnings.push(`Row ${rowNum}: Translated protein is very short (${proteinSequence.length} aa)`)
        }
      }
    }

    // Calculate activity score
    // Activity = (DNA_Yield / Protein_Yield) normalized by baseline
    let activityScore = 0
    if (proteinYield > 0 && baselineProtein > 0) {
      const normalizedDNA = dnaYield / (baselineDNA || 1)
      const normalizedProtein = proteinYield / baselineProtein
      // High DNA yield with low protein expression = high activity
      activityScore = normalizedDNA / Math.max(normalizedProtein, 0.1)
    }

    // Store for mutation tracking
    if (plasmidIndex !== undefined && plasmidIndex !== null) {
      variantsByIndex.set(plasmidIndex, { generation, mutations })
    }

    // Extract additional metadata
    const knownFields = [
      'Plasmid_Variant_Index', 'plasmid_variant_index',
      'Parent_Plasmid_Variant', 'parent_plasmid_variant',
      'Generation', 'generation',
      'Assembled_DNA_Sequence', 'assembled_dna_sequence',
      'DNA_Yield', 'dna_yield',
      'Protein_Yield', 'protein_yield',
      'Fluorescence', 'fluorescence',
      'Is_Control', 'is_control'
    ]
    
    const metadata: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(raw)) {
      if (!knownFields.includes(key)) {
        metadata[key] = value
      }
    }

    const variant: VariantData = {
      id: crypto.randomUUID(),
      experimentId,
      plasmidVariantIndex: plasmidIndex ?? 0,
      parentPlasmidVariant: parentIndex ?? null,
      generation,
      assembledDNASequence: dnaSequence,
      proteinSequence,
      dnaYield,
      proteinYield,
      fluorescence,
      activityScore,
      isControl,
      mutations,
      qcStatus,
      qcMessage,
      metadata,
    }

    variants.push(variant)
  }

  return { variants, errors, warnings }
}

function identifyMutations(
  wtSequence: string,
  variantSequence: string,
  generation: number,
  parentIndex: number | null | undefined,
  variantsByIndex: Map<number, { generation: number, mutations: Mutation[] }>
): Mutation[] {
  const mutations: Mutation[] = []
  const maxLength = Math.min(wtSequence.length, variantSequence.length)

  // Get parent mutations if available
  const parentMutations = parentIndex ? variantsByIndex.get(parentIndex)?.mutations || [] : []
  const inheritedPositions = new Set(parentMutations.map(m => m.position))

  for (let i = 0; i < maxLength; i++) {
    if (wtSequence[i] !== variantSequence[i]) {
      const isNew = !inheritedPositions.has(i + 1)
      
      mutations.push({
        position: i + 1,
        wildType: wtSequence[i],
        mutant: variantSequence[i],
        type: 'non-synonymous', // All AA changes are non-synonymous at protein level
        generation: isNew ? generation : (parentMutations.find(m => m.position === i + 1)?.generation ?? generation),
      })
    }
  }

  // Check for length differences
  if (variantSequence.length > wtSequence.length) {
    for (let i = wtSequence.length; i < variantSequence.length; i++) {
      mutations.push({
        position: i + 1,
        wildType: '-',
        mutant: variantSequence[i],
        type: 'non-synonymous',
        generation,
      })
    }
  }

  return mutations
}

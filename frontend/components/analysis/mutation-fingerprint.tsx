"use client"

import { useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { Dna, AlertCircle } from 'lucide-react'
import type { VariantData, Mutation } from '@/lib/types'

interface MutationFingerprintProps {
  variants: VariantData[]
  wtSequence: string
  selectedVariantIndex: number | null
  onSelectVariant: (index: number) => void
}

// Generation colors
const GENERATION_COLORS = [
  'bg-blue-500',
  'bg-green-500',
  'bg-yellow-500',
  'bg-orange-500',
  'bg-red-500',
  'bg-purple-500',
  'bg-pink-500',
  'bg-cyan-500',
  'bg-emerald-500',
  'bg-indigo-500',
]

export function MutationFingerprint({
  variants,
  wtSequence,
  selectedVariantIndex,
  onSelectVariant,
}: MutationFingerprintProps) {
  const selectedVariant = variants.find(v => v.plasmidVariantIndex === selectedVariantIndex)
  
  const generations = useMemo(() => {
    return [...new Set(variants.flatMap(v => v.mutations.map(m => m.generation)))].sort((a, b) => a - b)
  }, [variants])

  // Create position map for visualization
  const positionBlocks = useMemo(() => {
    if (!selectedVariant || !wtSequence) return []
    
    const blocks: Array<{
      position: number
      wt: string
      mut: string | null
      generation: number | null
      isMutated: boolean
    }> = []
    
    const mutationMap = new Map(
      selectedVariant.mutations.map(m => [m.position, m])
    )
    
    // Show only the region with mutations + some context
    const mutPositions = selectedVariant.mutations.map(m => m.position)
    if (mutPositions.length === 0) {
      // Show first 100 residues if no mutations
      for (let i = 1; i <= Math.min(100, wtSequence.length); i++) {
        blocks.push({
          position: i,
          wt: wtSequence[i - 1] || '-',
          mut: null,
          generation: null,
          isMutated: false,
        })
      }
    } else {
      const minPos = Math.max(1, Math.min(...mutPositions) - 10)
      const maxPos = Math.min(wtSequence.length, Math.max(...mutPositions) + 10)
      
      for (let i = minPos; i <= maxPos; i++) {
        const mutation = mutationMap.get(i)
        blocks.push({
          position: i,
          wt: wtSequence[i - 1] || '-',
          mut: mutation?.mutant || null,
          generation: mutation?.generation ?? null,
          isMutated: !!mutation,
        })
      }
    }
    
    return blocks
  }, [selectedVariant, wtSequence])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Dna className="h-5 w-5" />
          Mutation Fingerprint
        </CardTitle>
        <CardDescription>
          Visualize specific amino acid changes colored by generation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Variant selector */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label className="text-sm font-medium mb-2 block">Select Variant</label>
            <Select 
              value={selectedVariantIndex?.toString() || ''} 
              onValueChange={(v) => onSelectVariant(parseInt(v))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a top performer to view mutations" />
              </SelectTrigger>
              <SelectContent>
                {variants.map((v, idx) => (
                  <SelectItem key={v.id} value={v.plasmidVariantIndex.toString()}>
                    #{idx + 1} - Variant {v.plasmidVariantIndex} (Activity: {v.activityScore.toFixed(3)})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Generation legend */}
        {generations.length > 0 && (
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-medium">Generation Colors:</span>
            {generations.map((gen, idx) => (
              <div key={gen} className="flex items-center gap-1.5">
                <div className={cn('w-3 h-3 rounded', GENERATION_COLORS[idx % GENERATION_COLORS.length])} />
                <span className="text-xs text-muted-foreground">Gen {gen}</span>
              </div>
            ))}
          </div>
        )}

        {/* Fingerprint visualization */}
        {!selectedVariant ? (
          <div className="text-center py-8">
            <AlertCircle className="h-8 w-8 mx-auto text-muted-foreground/50 mb-2" />
            <p className="text-muted-foreground">
              Select a variant above to view its mutation fingerprint
            </p>
          </div>
        ) : selectedVariant.mutations.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-muted-foreground">
              This variant has no mutations compared to the wild type
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Variant info */}
            <div className="flex flex-wrap gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Variant:</span>{' '}
                <span className="font-mono font-medium">{selectedVariant.plasmidVariantIndex}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Generation:</span>{' '}
                <Badge variant="outline">Gen {selectedVariant.generation}</Badge>
              </div>
              <div>
                <span className="text-muted-foreground">Total Mutations:</span>{' '}
                <span className="font-medium">{selectedVariant.mutations.length}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Activity:</span>{' '}
                <span className="font-medium text-primary">{selectedVariant.activityScore.toFixed(3)}</span>
              </div>
            </div>

            {/* Sequence visualization */}
            <div className="border rounded-lg p-4 bg-muted/30 overflow-x-auto">
              <div className="font-mono text-xs space-y-1">
                {/* Position numbers row */}
                <div className="flex gap-0.5 text-muted-foreground">
                  {positionBlocks.map((block) => (
                    <div 
                      key={`pos-${block.position}`} 
                      className={cn(
                        'w-6 text-center',
                        block.isMutated && 'font-bold'
                      )}
                    >
                      {block.position % 10 === 0 ? block.position : ''}
                    </div>
                  ))}
                </div>
                
                {/* WT sequence row */}
                <div className="flex gap-0.5">
                  <span className="w-12 text-muted-foreground">WT:</span>
                  {positionBlocks.map((block) => (
                    <div 
                      key={`wt-${block.position}`}
                      className={cn(
                        'w-6 text-center rounded',
                        block.isMutated && 'line-through text-muted-foreground'
                      )}
                    >
                      {block.wt}
                    </div>
                  ))}
                </div>
                
                {/* Mutant sequence row */}
                <div className="flex gap-0.5">
                  <span className="w-12 text-muted-foreground">Mut:</span>
                  {positionBlocks.map((block) => {
                    const genIdx = block.generation !== null 
                      ? generations.indexOf(block.generation) 
                      : -1
                    
                    return (
                      <div 
                        key={`mut-${block.position}`}
                        className={cn(
                          'w-6 text-center rounded font-bold',
                          block.isMutated && genIdx >= 0 
                            ? `${GENERATION_COLORS[genIdx % GENERATION_COLORS.length]} text-white`
                            : 'text-muted-foreground/30'
                        )}
                        title={block.isMutated 
                          ? `${block.wt}${block.position}${block.mut} (Gen ${block.generation})`
                          : undefined
                        }
                      >
                        {block.mut || block.wt}
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>

            {/* Mutation list */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Mutation Details</h4>
              <div className="flex flex-wrap gap-2">
                {selectedVariant.mutations.map((mut, idx) => {
                  const genIdx = generations.indexOf(mut.generation)
                  return (
                    <Badge 
                      key={idx}
                      variant="outline"
                      className={cn(
                        'font-mono',
                        genIdx >= 0 && `border-2`,
                      )}
                      style={{
                        borderColor: genIdx >= 0 
                          ? getColorFromClass(GENERATION_COLORS[genIdx % GENERATION_COLORS.length])
                          : undefined
                      }}
                    >
                      {mut.wildType}{mut.position}{mut.mutant}
                      <span className="ml-1 text-muted-foreground">(Gen {mut.generation})</span>
                    </Badge>
                  )
                })}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Helper to convert Tailwind class to actual color
function getColorFromClass(className: string): string {
  const colorMap: Record<string, string> = {
    'bg-blue-500': '#3b82f6',
    'bg-green-500': '#22c55e',
    'bg-yellow-500': '#eab308',
    'bg-orange-500': '#f97316',
    'bg-red-500': '#ef4444',
    'bg-purple-500': '#a855f7',
    'bg-pink-500': '#ec4899',
    'bg-cyan-500': '#06b6d4',
    'bg-emerald-500': '#10b981',
    'bg-indigo-500': '#6366f1',
  }
  return colorMap[className] || '#888888'
}

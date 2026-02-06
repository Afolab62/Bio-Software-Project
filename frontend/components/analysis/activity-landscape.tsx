"use client"

import { useMemo } from 'react'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  ZAxis,
  Cell,
} from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart'
import { Mountain, Info } from 'lucide-react'
import type { VariantData } from '@/lib/types'

interface ActivityLandscapeProps {
  variants: VariantData[]
}

export function ActivityLandscape({ variants }: ActivityLandscapeProps) {
  // Perform simple dimensionality reduction using mutation count and generation
  // For a real implementation, you would use PCA or t-SNE
  const landscapeData = useMemo(() => {
    if (variants.length === 0) return []
    
    // Normalize values for visualization
    const maxActivity = Math.max(...variants.map(v => v.activityScore))
    const maxMutations = Math.max(...variants.map(v => v.mutations.length), 1)
    const maxGen = Math.max(...variants.map(v => v.generation), 1)
    
    return variants.map(v => {
      // Simple 2D projection based on mutations and generation
      // Add some jitter to avoid overlap
      const jitterX = (Math.random() - 0.5) * 0.1
      const jitterY = (Math.random() - 0.5) * 0.1
      
      return {
        id: v.id,
        variantIndex: v.plasmidVariantIndex,
        x: (v.mutations.length / maxMutations) + jitterX,
        y: (v.generation / maxGen) + jitterY,
        activity: v.activityScore,
        normalizedActivity: v.activityScore / maxActivity,
        generation: v.generation,
        mutations: v.mutations.length,
      }
    })
  }, [variants])

  // Get color based on activity score
  const getActivityColor = (normalizedActivity: number) => {
    // Gradient from blue (low) to green (medium) to yellow/red (high)
    if (normalizedActivity < 0.33) {
      return `hsl(200, 60%, ${40 + normalizedActivity * 60}%)`
    } else if (normalizedActivity < 0.66) {
      return `hsl(${200 - (normalizedActivity - 0.33) * 240}, 60%, 50%)`
    } else {
      return `hsl(${120 - (normalizedActivity - 0.66) * 360}, 70%, 50%)`
    }
  }

  if (variants.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Mountain className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground">No data available for landscape visualization</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mountain className="h-5 w-5" />
          Activity Landscape
        </CardTitle>
        <CardDescription>
          2D projection of variant space with activity scores as color intensity
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-start gap-2 p-3 rounded-lg bg-muted/50 text-sm">
          <Info className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
          <p className="text-muted-foreground">
            This visualization projects variants into 2D space based on mutation count (X-axis) 
            and generation (Y-axis). Point color indicates activity score - brighter colors 
            represent higher activity. For production use, consider implementing PCA or t-SNE 
            for more accurate sequence-based dimensionality reduction.
          </p>
        </div>

        {/* Color legend */}
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium">Activity:</span>
          <div className="flex items-center gap-1">
            <div className="w-16 h-3 rounded" style={{
              background: 'linear-gradient(to right, hsl(200, 60%, 40%), hsl(160, 60%, 50%), hsl(80, 70%, 50%), hsl(40, 70%, 50%))'
            }} />
            <div className="flex justify-between w-16 text-xs text-muted-foreground">
              <span>Low</span>
              <span>High</span>
            </div>
          </div>
        </div>

        <ChartContainer
          config={{
            activity: {
              label: "Activity Score",
              color: "hsl(160, 60%, 50%)",
            },
          }}
          className="h-[400px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis 
                type="number"
                dataKey="x" 
                name="Mutation Density"
                domain={[-0.1, 1.1]}
                tickFormatter={() => ''}
                label={{ value: 'Mutation Count (normalized)', position: 'bottom', offset: 0 }}
                className="text-muted-foreground"
              />
              <YAxis 
                type="number"
                dataKey="y"
                name="Generation"
                domain={[-0.1, 1.1]}
                tickFormatter={() => ''}
                label={{ value: 'Generation (normalized)', angle: -90, position: 'insideLeft' }}
                className="text-muted-foreground"
              />
              <ZAxis 
                type="number" 
                dataKey="activity" 
                range={[50, 400]}
                name="Activity"
              />
              <ChartTooltip 
                content={
                  <ChartTooltipContent 
                    formatter={(value, name, item) => {
                      const payload = item.payload
                      if (!payload) return [String(value), String(name)]
                      return [
                        <div key="tooltip" className="space-y-1">
                          <div><strong>Variant {payload.variantIndex}</strong></div>
                          <div>Generation: {payload.generation}</div>
                          <div>Mutations: {payload.mutations}</div>
                          <div>Activity: {payload.activity.toFixed(3)}</div>
                        </div>,
                        ''
                      ]
                    }}
                  />
                }
              />
              <Scatter 
                name="Variants" 
                data={landscapeData}
              >
                {landscapeData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={getActivityColor(entry.normalizedActivity)}
                    strokeWidth={1}
                    stroke="rgba(0,0,0,0.2)"
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </ChartContainer>

        {/* Summary statistics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t">
          <div>
            <p className="text-sm text-muted-foreground">Total Points</p>
            <p className="text-lg font-bold">{landscapeData.length}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Generations</p>
            <p className="text-lg font-bold">
              {new Set(variants.map(v => v.generation)).size}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Max Mutations</p>
            <p className="text-lg font-bold">
              {Math.max(...variants.map(v => v.mutations.length))}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Activity Range</p>
            <p className="text-lg font-bold">
              {Math.min(...variants.map(v => v.activityScore)).toFixed(2)} - {Math.max(...variants.map(v => v.activityScore)).toFixed(2)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

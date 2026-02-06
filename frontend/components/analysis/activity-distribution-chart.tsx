"use client"

import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart'
import { BarChart3 } from 'lucide-react'
import type { VariantData, GenerationStats } from '@/lib/types'

interface ActivityDistributionChartProps {
  variants: VariantData[]
}

export function ActivityDistributionChart({ variants }: ActivityDistributionChartProps) {
  const generationStats = useMemo(() => {
    const generations = [...new Set(variants.map(v => v.generation))].sort((a, b) => a - b)
    
    return generations.map(gen => {
      const genVariants = variants.filter(v => v.generation === gen)
      const scores = genVariants.map(v => v.activityScore).sort((a, b) => a - b)
      
      const mean = scores.reduce((s, v) => s + v, 0) / scores.length
      const median = scores[Math.floor(scores.length / 2)] || 0
      const min = Math.min(...scores)
      const max = Math.max(...scores)
      
      // Calculate std dev
      const squaredDiffs = scores.map(s => Math.pow(s - mean, 2))
      const avgSquaredDiff = squaredDiffs.reduce((s, v) => s + v, 0) / scores.length
      const stdDev = Math.sqrt(avgSquaredDiff)

      return {
        generation: gen,
        count: genVariants.length,
        meanActivity: mean,
        medianActivity: median,
        minActivity: min,
        maxActivity: max,
        stdDev,
      } as GenerationStats
    })
  }, [variants])

  // Compute colors in JS - hsl values for chart colors
  const getBarColor = (index: number) => {
    const hues = [200, 160, 280, 80, 25] // chart-1 through chart-5 hue approximations
    const hue = hues[index % hues.length]
    return `hsl(${hue}, 60%, 50%)`
  }

  if (generationStats.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground">No generation data available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Activity Distribution by Generation
        </CardTitle>
        <CardDescription>
          Mean activity score per generation showing evolution progress
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={{
            meanActivity: {
              label: "Mean Activity",
              color: "hsl(200, 60%, 50%)",
            },
            maxActivity: {
              label: "Max Activity",
              color: "hsl(160, 60%, 50%)",
            },
          }}
          className="h-[350px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={generationStats} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis 
                dataKey="generation" 
                tickFormatter={(v) => `Gen ${v}`}
                className="text-muted-foreground"
              />
              <YAxis 
                label={{ value: 'Activity Score', angle: -90, position: 'insideLeft' }}
                className="text-muted-foreground"
              />
              <ChartTooltip 
                content={
                  <ChartTooltipContent 
                    formatter={(value, name) => {
                      if (name === 'meanActivity') return [`${Number(value).toFixed(3)}`, 'Mean Activity']
                      if (name === 'maxActivity') return [`${Number(value).toFixed(3)}`, 'Max Activity']
                      return [String(value), String(name)]
                    }}
                  />
                }
              />
              <Bar 
                dataKey="meanActivity" 
                name="meanActivity"
                radius={[4, 4, 0, 0]}
              >
                {generationStats.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getBarColor(index)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartContainer>

        {/* Generation summary table */}
        <div className="mt-6 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-2 font-medium">Generation</th>
                <th className="text-left py-2 px-2 font-medium">Variants</th>
                <th className="text-left py-2 px-2 font-medium">Mean</th>
                <th className="text-left py-2 px-2 font-medium">Median</th>
                <th className="text-left py-2 px-2 font-medium">Min</th>
                <th className="text-left py-2 px-2 font-medium">Max</th>
                <th className="text-left py-2 px-2 font-medium">Std Dev</th>
              </tr>
            </thead>
            <tbody>
              {generationStats.map((stat) => (
                <tr key={stat.generation} className="border-b">
                  <td className="py-2 px-2 font-medium">Gen {stat.generation}</td>
                  <td className="py-2 px-2">{stat.count}</td>
                  <td className="py-2 px-2 font-mono">{stat.meanActivity.toFixed(3)}</td>
                  <td className="py-2 px-2 font-mono">{stat.medianActivity.toFixed(3)}</td>
                  <td className="py-2 px-2 font-mono text-muted-foreground">{stat.minActivity.toFixed(3)}</td>
                  <td className="py-2 px-2 font-mono text-accent">{stat.maxActivity.toFixed(3)}</td>
                  <td className="py-2 px-2 font-mono text-muted-foreground">{stat.stdDev.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

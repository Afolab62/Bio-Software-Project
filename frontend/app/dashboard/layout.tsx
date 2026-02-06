"use client"

import React from "react"

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { DashboardNav } from '@/components/dashboard-nav'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const { user, isLoading } = useAuth()

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/')
    }
  }, [user, isLoading, router])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-background">
      <DashboardNav />
      <main className="lg:pl-64">
        <div className="p-6 lg:p-8">
          {children}
        </div>
      </main>
    </div>
  )
}

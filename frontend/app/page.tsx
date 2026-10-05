import { AnalyseSection } from '@/components/analyse/analyse-section'
import { Hero } from '@/components/hero'
import { HowItWorks } from '@/components/how-it-works'
import { PerformanceSection } from '@/components/performance-section'
import { ScopeSection, SiteFooter } from '@/components/scope-section'
import { SiteHeader } from '@/components/site-header'

export default function Page() {
  return (
    <>
      <SiteHeader />
      <main className="overflow-x-clip">
        <Hero />
        <HowItWorks />
        <AnalyseSection />
        <PerformanceSection />
        <ScopeSection />
      </main>
      <SiteFooter />
    </>
  )
}
